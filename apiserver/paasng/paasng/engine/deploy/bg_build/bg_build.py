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
from typing import TYPE_CHECKING, Dict
from uuid import UUID

from blue_krill.redis_tools.messaging import StreamChannel
from celery import shared_task
from django.conf import settings
from django.utils.encoding import force_text

from paas_wl.platform.applications.constants import ArtifactType

# NOTE: The background building process depends on the paas_wl package.
from paas_wl.platform.applications.models.build import Build, BuildProcess
from paas_wl.resources.base.exceptions import PodNotSucceededError, ReadTargetStatusTimeout, ResourceDuplicate
from paas_wl.resources.utils.app import get_scheduler_client_by_app
from paas_wl.utils.kubestatus import check_pod_health_status
from paasng.engine.constants import BuildStatus
from paasng.engine.deploy.bg_build.utils import (
    SlugBuilderTemplate,
    generate_builder_env_vars,
    generate_builder_name,
    generate_launcher_env_vars,
    generate_slug_path,
    prepare_slugbuilder_template,
)
from paasng.engine.exceptions import DeployInterruptionFailed
from paasng.engine.models.deployment import Deployment
from paasng.engine.models.phases import DeployPhaseTypes
from paasng.engine.utils.output import ConsoleStream, DeployStream, RedisWithModelStream, Style
from paasng.engine.workflow import DeployStep
from paasng.platform.core.storages.redisdb import get_default_redis

if TYPE_CHECKING:
    from paas_wl.platform.applications.models import WlApp

logger = logging.getLogger(__name__)

# Max timeout seconds for waiting the slugbuilder pod to become ready
_WAIT_FOR_READINESS_TIMEOUT = 300
_FOLLOWING_LOGS_TIMEOUT = 300


@shared_task
def start_bg_build_process(deploy_id, bp_id, stream_channel_id=None, metadata=None):
    """Start a new build process which starts a builder to build a slug and deploy
    it to the app cluster.

    :param deploy_id: The ID of the deployment object.
    :param bp_id: The ID of the build process object.
    """
    build_process = BuildProcess.objects.get(pk=bp_id)
    # Make a new channel if stream_channel_id is given

    stream: DeployStream
    if stream_channel_id:
        stream_channel = StreamChannel(stream_channel_id, redis_db=get_default_redis())
        stream_channel.initialize()
        stream = RedisWithModelStream(build_process, stream_channel)
    else:
        stream = ConsoleStream()

    bp_executor = BuildProcessExecutor(Deployment.objects.get(pk=deploy_id), build_process, stream)
    bp_executor.execute(metadata=metadata)


def interrupt_build_proc(bp_id: UUID) -> bool:
    """Interrupt a build process

    :return: Whether the build process was successfully interrupted.
    :raises: DeployInterruptionFailed if the build process is not interruptable.
    """
    bp = BuildProcess.objects.get(pk=bp_id)
    if not bp.check_interruption_allowed():
        raise DeployInterruptionFailed()

    bp.set_int_requested_at()
    app = bp.app
    result = get_scheduler_client_by_app(app).interrupt_builder(app.namespace, name=generate_builder_name(app))
    return result


class BuildProcessExecutor(DeployStep):
    """Execute a build process, it's a blocking operation and should be executed
    in a celery task."""

    PHASE_TYPE = DeployPhaseTypes.BUILD

    def __init__(self, deployment: Deployment, bp: BuildProcess, stream: DeployStream):
        super().__init__(deployment, stream)

        self.bp = bp
        self.wl_app: 'WlApp' = bp.app
        self._builder_name = generate_builder_name(self.wl_app)

    def execute(self, metadata: Dict):
        """Execute the build process"""
        try:
            with self.procedure("准备构建环境"):
                # 初始化 k8s 调度器
                self.scheduler_client = get_scheduler_client_by_app(self.wl_app)

            with self.procedure("构建环境变量"):
                env_vars = generate_builder_env_vars(self.bp, metadata)

            with self.procedure("启动构建任务"):
                self.stream.write_message(f"Preparing to build {self.wl_app.name} ...")
                slugbuilder_template = prepare_slugbuilder_template(self.wl_app, env_vars, builder_image=self.bp.image)

                self.stream.write_message(f"Starting build app: {self.wl_app.name}")
                self.start_slugbuilder(slugbuilder_template)

            with self.procedure("构建任务准备中"):
                self.scheduler_client.wait_build_logs_readiness(
                    self.wl_app.namespace, name=self._builder_name, timeout=_WAIT_FOR_READINESS_TIMEOUT
                )

            self.bp.set_logs_was_ready()
            self.start_following_logs()

            # 绑定Build对象
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
                name=self._builder_name, follow=True, timeout=_FOLLOWING_LOGS_TIMEOUT, namespace=self.wl_app.namespace
            ):
                line = force_text(line)
                self.stream.write_message(line)
        except Exception:
            logger.warning("failed to watch build logs for App: %s", self.wl_app.name)
            # 解析失败，直接将当前步骤置为失败
            self.stream.write_title("构建失败")
            self.stream.write_message("building process failed.")
            raise
        else:
            self.wait_for_succeeded()
        finally:
            # 不管构建成功与否, 均需要清理 slugbuilder 容器
            self.clean_slugbuilder()

    def wait_for_succeeded(self):
        """Wait for pod to become succeeded"""
        # The phase of a kubernetes pod was managed in a fully async way, there is not guarantee
        # it will transfer into "success/failed" immediately after "follow_build_logs"
        # call finishes. So we will wait a reasonable long period such as 60 seconds.
        self.scheduler_client.wait_build_succeeded(self.wl_app.namespace, name=self._builder_name, timeout=60)

    def start_slugbuilder(self, pod_template: SlugBuilderTemplate) -> str:
        """Start a slugbuilder from pod_template

        :return slug_builder_name"""
        self.scheduler_client.ensure_namespace(pod_template.namespace)
        self.scheduler_client.ensure_image_credentials_secret(self.wl_app)

        try:
            slug_builder_name = self.scheduler_client.build_slug(template=pod_template)
        except ResourceDuplicate as e:
            logger.exception("Duplicate slug-builder Pod exists")
            self.stream.write_message(Style.Error(f"上一次构建未正常退出, 请在{e.extra_value}重试."))
            raise

        logger.debug('SlugBuilder created: %s', slug_builder_name)
        return slug_builder_name

    def create_and_bind_build_instance(self, metadata: Dict) -> Build:
        """Create the Build instance and bind it to self.BuildProcess instance

        :param dict metadata: Metadata to be stored in Build instance, such as `procfile`
        """
        procfile = {}
        if 'procfile' in metadata:
            procfile = metadata['procfile']
        if 'image' not in metadata:
            raise KeyError("'image' is required")
        image = metadata['image']
        artifact_type = ArtifactType.SLUG
        if metadata.get("use_dockerfile") or metadata.get("use_cnb"):
            artifact_type = ArtifactType.IMAGE
        bkapp_revision_id = metadata.get("bkapp_revision_id", None)

        # starting create build
        build_instance = Build.objects.create(
            owner=settings.BUILDER_USERNAME,
            app=self.wl_app,
            slug_path=generate_slug_path(self.bp),
            image=image,
            branch=self.bp.branch,
            revision=self.bp.revision,
            procfile=procfile,
            env_variables=generate_launcher_env_vars(slug_path=generate_slug_path(self.bp)),
            bkapp_revision_id=bkapp_revision_id,
            artifact_type=artifact_type,
        )

        # retrieve bp object again, flush the status
        self.bp.build = build_instance
        self.bp.status = BuildStatus.SUCCESSFUL.value
        self.bp.save(update_fields=["build", "status"])
        return build_instance

    def clean_slugbuilder(self):
        try:
            self.scheduler_client.delete_builder(namespace=self.wl_app.namespace, name=self._builder_name)
        except Exception as e:
            # cleaning should not influenced main process
            logger.warning("清理应用 %s 的 slug builder 失败, 原因: %s", self.wl_app.name, e)
