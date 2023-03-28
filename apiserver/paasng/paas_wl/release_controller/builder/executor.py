# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from functools import partial
from typing import TYPE_CHECKING, Dict, Optional

from django.conf import settings
from django.utils.encoding import force_text

from paas_wl.platform.applications.models.build import Build, BuildProcess
from paas_wl.release_controller.builder.infras import BuildProcedure, SlugBuilderTemplate
from paas_wl.release_controller.builder.procedures import (
    generate_builder_env_vars,
    generate_builder_name,
    generate_launcher_env_vars,
    generate_slug_path,
    prepare_slugbuilder_template,
)
from paas_wl.resources.base.exceptions import PodNotSucceededError, ReadTargetStatusTimeout, ResourceDuplicate
from paas_wl.resources.utils.app import get_scheduler_client_by_app
from paas_wl.utils.constants import BuildStatus
from paas_wl.utils.kubestatus import check_pod_health_status
from paas_wl.utils.stream import Stream
from paas_wl.utils.termcolors import Style

if TYPE_CHECKING:
    from paas_wl.platform.applications.models import WlApp

logger = logging.getLogger(__name__)

# Max timeout seconds for waiting the slugbuilder pod to become ready
_WAIT_FOR_READINESS_TIMEOUT = 300
_FOLLOWING_LOGS_TIMEOUT = 300


class BuildProcessExecutor:
    """Executor for BuildProcess object"""

    def __init__(self, bp: BuildProcess, stream: Stream):
        self.bp = bp
        self.app: 'WlApp' = bp.app
        self.stream = stream

        self.procedure = partial(BuildProcedure, stream)
        self._builder_name = generate_builder_name(self.app)

    def execute(self, metadata: Optional[Dict] = None):
        """Execute the build process"""
        try:
            with self.procedure("准备构建环境"):
                # 初始化 k8s 调度器
                self.scheduler_client = get_scheduler_client_by_app(self.app)

            with self.procedure("构建环境变量"):
                env_vars = generate_builder_env_vars(self.bp, metadata)

            with self.procedure("启动构建任务"):
                self.stream.write_message(f"Preparing to build {self.app.name} ...")
                slugbuilder_template = prepare_slugbuilder_template(self.app, env_vars, metadata)

                self.stream.write_message(f"Starting build app: {self.app.name}")
                self.start_slugbuilder(slugbuilder_template)

            with self.procedure("构建任务准备中"):
                self.scheduler_client.wait_build_logs_readiness(
                    self.app.namespace, name=self._builder_name, timeout=_WAIT_FOR_READINESS_TIMEOUT
                )

            self.bp.set_logs_was_ready()
            self.start_following_logs()

            with self.procedure("绑定Build对象", write_to_console=True):
                build_instance = self.create_and_bind_build_instance(metadata=metadata)
                self.stream.write_message('Generated build id: %s' % build_instance.uuid)
        except ReadTargetStatusTimeout as e:
            logger.exception(
                f"builder pod did not reach the target status within the timeout period during deploy[{self.bp}]"
            )
            self.bp.update_status(BuildStatus.FAILED)
            pod = e.extra_value
            if pod is None:
                self.stream.write_message(
                    Style.Error("Pod is not created normally, please contact the cluster administrator.")
                )
            else:
                health_status = check_pod_health_status(pod)
                msg = (
                    health_status.message
                    or f"containers are not in terminated or waiting state and pod status: {pod.status.phase}"
                )
                self.stream.write_message(Style.Error(msg))
        except PodNotSucceededError as e:
            # Load the latest content from database, if an interruption was requested for current bp
            self.bp.refresh_from_db()
            if self.bp.int_requested_at:
                self.stream.write_title("构建已中止")
                self.stream.write_message("building process was interrupted.")
                self.bp.update_status(BuildStatus.INTERRUPTED.value)
            else:
                logger.exception(f"builder pod exit not succeeded during deploy[{self.bp}]")
                self.stream.write_title("构建失败")
                self.stream.write_message(Style.Error(e.message))
                self.bp.update_status(BuildStatus.FAILED)
        except Exception:
            logger.exception(f"A critical error happened during deploy[{self.bp}]")
            self.bp.update_status(BuildStatus.FAILED.value)
        else:
            self.stream.write_title("构建完成")
            self.stream.write_message("building process finished.")

    def start_following_logs(self):
        """Start following logs generated by builder process"""
        try:
            # User interruption was allowed when first log message was received — which means the Pod
            # has entered "Running" status.
            for line in self.scheduler_client.get_build_log(
                name=self._builder_name, follow=True, timeout=_FOLLOWING_LOGS_TIMEOUT, namespace=self.app.namespace
            ):
                line = force_text(line)
                self.stream.write_message(line)
        except Exception:
            logger.warning("failed to watch build logs for App: %s", self.app.name)
            # 解析失败，直接将当前步骤置为失败
            self.stream.write_title("构建失败")
            self.stream.write_message("building process failed.")
            raise
        else:
            self.wait_for_succeeded()
        finally:
            # 不管构建成功与否, 均需要清理 slugbuilder 容器
            with self.procedure("清除构建容器", write_to_console=True):
                self.clean_slugbuilder()

    def wait_for_succeeded(self):
        """Wait for pod to become succeeded"""
        # The phase of a kubernetes pod was managed in a fully async way, there is not guarantee
        # it will transfer into "success/failed" immediately after "follow_build_logs"
        # call finishes. So we will wait a reasonable long period such as 60 seconds.
        self.scheduler_client.wait_build_succeeded(self.app.namespace, name=self._builder_name, timeout=60)

    def start_slugbuilder(self, pod_template: SlugBuilderTemplate) -> str:
        """Start a slugbuilder from pod_template

        :return slug_builder_name"""
        self.scheduler_client.ensure_namespace(pod_template.namespace)
        self.scheduler_client.ensure_image_credentials_secret(self.app)

        try:
            slug_builder_name = self.scheduler_client.build_slug(template=pod_template)
        except ResourceDuplicate as e:
            logger.exception("Duplicate slug-builder Pod exists")
            self.stream.write_message(Style.Error(f"上一次构建未正常退出, 请在{e.extra_value}重试."))
            raise

        logger.debug('SlugBuilder created: %s', slug_builder_name)
        return slug_builder_name

    def create_and_bind_build_instance(self, metadata: Optional[Dict] = None) -> Build:
        """Create the Build instance and bind it to self.BuildProcess instance

        :param dict metadata: Metadata to be stored in Build instance, such as `procfile`
        """
        procfile = {}
        if metadata and 'procfile' in metadata:
            procfile = metadata['procfile']

        # starting create build
        build_instance = Build.objects.create(
            owner=settings.BUILDER_USERNAME,
            app=self.app,
            slug_path=generate_slug_path(self.bp),
            branch=self.bp.branch,
            revision=self.bp.revision,
            procfile=procfile,
            env_variables=generate_launcher_env_vars(slug_path=generate_slug_path(self.bp)),
        )

        # retrieve bp object again, flush the status
        self.bp.build = build_instance
        self.bp.status = BuildStatus.SUCCESSFUL.value
        self.bp.save(update_fields=["build", "status"])
        return build_instance

    def clean_slugbuilder(self):
        try:
            self.scheduler_client.delete_builder(namespace=self.app.namespace, name=self._builder_name)
        except Exception as e:
            # cleaning should not influenced main process
            logger.warning("清理应用 %s 的 slug builder 失败, 原因: %s", self.app.name, e)


def interrupt_build(bp: BuildProcess) -> bool:
    """Interrupt a build process

    :param bp: BuildProcess object
    """
    bp.set_int_requested_at()
    app = bp.app
    result = get_scheduler_client_by_app(app).interrupt_builder(app.namespace, name=generate_builder_name(app))
    return result
