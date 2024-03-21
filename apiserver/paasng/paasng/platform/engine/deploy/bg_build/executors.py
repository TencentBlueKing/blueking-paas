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
import base64
import json
import logging
import re
import time
from typing import TYPE_CHECKING, Dict

from django.conf import settings
from django.utils.encoding import force_text

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.applications.models.build import Build, BuildProcess, mark_as_latest_artifact
from paas_wl.bk_app.deploy.app_res.controllers import BuildHandler, NamespacesHandler, ensure_image_credentials_secret
from paas_wl.infras.resources.base.exceptions import PodNotSucceededError, ReadTargetStatusTimeout, ResourceDuplicate
from paas_wl.utils.kubestatus import check_pod_health_status
from paasng.platform.bk_devops import definitions
from paasng.platform.bk_devops.client import PipelineController
from paasng.platform.bk_devops.constants import PipelineBuildStatus
from paasng.platform.bk_devops.exceptions import BkDevopsGatewayServiceError
from paasng.platform.engine.constants import BuildStatus
from paasng.platform.engine.deploy.bg_build.exceptions import (
    DevopsPipelineBuildNotSuccess,
    DevopsPipelineBuildUnsupported,
)
from paasng.platform.engine.deploy.bg_build.utils import (
    SlugBuilderTemplate,
    generate_builder_env_vars,
    generate_builder_name,
    generate_launcher_env_vars,
    generate_slug_path,
    prepare_slugbuilder_template,
)
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.phases import DeployPhaseTypes
from paasng.platform.engine.utils.output import DeployStream, Style
from paasng.platform.engine.workflow import DeployStep
from paasng.utils.basic import get_username_by_bkpaas_user_id

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import WlApp

logger = logging.getLogger(__name__)

# Max timeout seconds for waiting the slugbuilder pod to become ready
_WAIT_FOR_READINESS_TIMEOUT = 300
_FOLLOWING_LOGS_TIMEOUT = 300


class K8sBuildProcessExecutor(DeployStep):
    """
    Execute a build process, using k8s pod to build and upload image or slug package,
    it's a blocking operation and should be executed in a celery task.
    """

    PHASE_TYPE = DeployPhaseTypes.BUILD

    def __init__(self, deployment: Deployment, bp: BuildProcess, stream: DeployStream):
        super().__init__(deployment, stream)

        self.bp = bp
        self.wl_app: "WlApp" = bp.app
        self._builder_name = generate_builder_name(self.wl_app)

    def execute(self, metadata: Dict):
        """Execute the build process"""
        try:
            with self.procedure("准备构建环境"):
                # 初始化 k8s 调度器
                self.build_handler = BuildHandler.new_by_app(self.wl_app)
                self.ns_handler = NamespacesHandler.new_by_app(self.wl_app)

            with self.procedure("构建环境变量"):
                env_vars = generate_builder_env_vars(self.bp, metadata)

            with self.procedure("启动构建任务"):
                self.stream.write_message(f"Preparing to build {self.wl_app.name} ...")
                slugbuilder_template = prepare_slugbuilder_template(self.wl_app, env_vars, builder_image=self.bp.image)

                self.stream.write_message(f"Starting build app: {self.wl_app.name}")
                self.start_slugbuilder(slugbuilder_template)

            with self.procedure("构建任务准备中"):
                self.build_handler.wait_for_logs_readiness(
                    self.wl_app.namespace, name=self._builder_name, timeout=_WAIT_FOR_READINESS_TIMEOUT
                )

            self.bp.set_logs_was_ready()
            self.start_following_logs()

            # 绑定Build对象
            build_instance = self.create_and_bind_build_instance(metadata=metadata)
            self.stream.write_message("Generated build id: %s" % build_instance.uuid)
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
                self.bp.update_status(BuildStatus.INTERRUPTED)
            else:
                logger.exception(f"builder pod exit not succeeded during deploy[{self.bp}]")
                self.stream.write_title("构建失败")
                self.stream.write_message(Style.Error(e.message))
                self.bp.update_status(BuildStatus.FAILED)
        except Exception:
            logger.exception(f"A critical error happened during deploy[{self.bp}]")
            self.bp.update_status(BuildStatus.FAILED)
        else:
            self.stream.write_title("构建完成")
            self.stream.write_message("building process finished.")

    def start_following_logs(self):
        """Start following logs generated by builder process"""
        try:
            # User interruption was allowed when first log message was received — which means the Pod
            # has entered "Running" status.
            for raw_line in self.build_handler.get_build_log(
                name=self._builder_name, follow=True, timeout=_FOLLOWING_LOGS_TIMEOUT, namespace=self.wl_app.namespace
            ):
                line = force_text(raw_line)
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
        self.build_handler.wait_for_succeeded(self.wl_app.namespace, name=self._builder_name, timeout=60)

    def start_slugbuilder(self, pod_template: SlugBuilderTemplate) -> str:
        """Start a slugbuilder from pod_template

        :return slug_builder_name"""
        self.ns_handler.ensure_namespace(pod_template.namespace)
        ensure_image_credentials_secret(self.wl_app)

        try:
            slug_builder_name = self.build_handler.build_slug(template=pod_template)
        except ResourceDuplicate as e:
            logger.exception("Duplicate slug-builder Pod exists")
            self.stream.write_message(Style.Error(f"上一次构建未正常退出, 请在{e.extra_value}重试."))
            raise

        logger.debug("SlugBuilder created: %s", slug_builder_name)
        return slug_builder_name

    def create_and_bind_build_instance(self, metadata: Dict) -> Build:
        """Create the Build instance and bind it to self.BuildProcess instance

        :param dict metadata: Metadata to be stored in Build instance, such as `procfile`
        """
        if "image" not in metadata:
            raise KeyError("'image' is required")
        image = metadata["image"]
        artifact_type = ArtifactType.SLUG
        artifact_metadata = {}
        if metadata.get("use_dockerfile") or metadata.get("use_cnb"):
            artifact_type = ArtifactType.IMAGE
            artifact_metadata["use_dockerfile"] = metadata.get("use_dockerfile", False)
            artifact_metadata["use_cnb"] = metadata.get("use_cnb", False)
        bkapp_revision_id = metadata.get("bkapp_revision_id", None)

        # starting create build
        build_instance = Build.objects.create(
            owner=self.deployment.operator,
            application_id=self.bp.application_id,
            module_id=self.bp.module_id,
            app=self.wl_app,
            slug_path=generate_slug_path(self.bp),
            image=image,
            branch=self.bp.branch,
            revision=self.bp.revision,
            env_variables=generate_launcher_env_vars(slug_path=generate_slug_path(self.bp)),
            bkapp_revision_id=bkapp_revision_id,
            artifact_type=artifact_type,
            artifact_metadata=artifact_metadata,
        )
        mark_as_latest_artifact(build_instance)

        # retrieve bp object again, flush the status
        self.bp.build = build_instance
        self.bp.save(update_fields=["build"])
        self.bp.update_status(BuildStatus.SUCCESSFUL)
        return build_instance

    def clean_slugbuilder(self):
        try:
            self.build_handler.delete_builder(namespace=self.wl_app.namespace, name=self._builder_name)
        except Exception as e:
            # cleaning should not influence main process
            logger.warning("清理应用 %s 的 slug builder 失败, 原因: %s", self.wl_app.name, e)


class DevopsPipelineBuildProcessExecutor(DeployStep):
    """
    Execute a build process, using devops pipeline to build and upload image,
    it's a blocking operation and should be executed in a celery task.
    """

    PHASE_TYPE = DeployPhaseTypes.BUILD
    FOLLOWING_LOGS_INTERVAL = 2
    DEVOPS_LOG_LEVEL_TAG_REGEX = re.compile("##\\[\\w+\\]")

    def __init__(self, deployment: Deployment, bp: BuildProcess, stream: DeployStream):
        super().__init__(deployment, stream)

        self.bp = bp
        self.wl_app: "WlApp" = bp.app
        # 注：蓝盾只提供了正式环境的 API
        bk_username = get_username_by_bkpaas_user_id(bp.owner)
        self.ctl = PipelineController(bk_username=bk_username)

        if not (settings.BKPAAS_DEVOPS_PROJECT_ID and settings.BKPAAS_CNB_PIPELINE_ID):
            raise DevopsPipelineBuildUnsupported("build image with devops pipeline unsupported")

    def execute(self, metadata: Dict):
        """Execute the build process"""
        try:
            with self.procedure("构建环境变量"):
                env_vars = generate_builder_env_vars(self.bp, metadata)

            with self.procedure("启动构建任务"):
                self.stream.write_message(f"Preparing to build {self.wl_app.name} ...")

                self.stream.write_message(f"Starting build app: {self.wl_app.name}")
                pipeline_build = self._start_devops_pipeline(env_vars)

            with self.procedure("等待构建完成"):
                self.bp.set_logs_was_ready()
                self._start_following_logs(pipeline_build)

            with self.procedure("检查构建结果"):
                self._ensure_pipeline_build_success(pipeline_build)

            # 若构建成功，则绑定 Build 实例
            build_inst = self._create_and_bind_build_instance(metadata=metadata)
            self.stream.write_message("Generated build id: %s" % build_inst.uuid)

        except BkDevopsGatewayServiceError:
            logger.exception(f"call devops pipeline failed during deploy[{self.bp}]")
            self.stream.write_message(Style.Error("Call devops pipeline failed, please contact the administrator"))
            self.bp.update_status(BuildStatus.FAILED)
        except Exception:
            logger.exception(f"critical error happened during deploy[{self.bp}]")
            self.bp.update_status(BuildStatus.FAILED)
        else:
            self.stream.write_title("构建完成")
            self.stream.write_message("building process finished.")

    def _start_devops_pipeline(self, env_vars: Dict[str, str]) -> definitions.PipelineBuild:
        """启动蓝盾流水线以构建镜像"""
        pipeline = definitions.Pipeline(
            projectId=settings.BKPAAS_DEVOPS_PROJECT_ID, pipelineId=settings.BKPAAS_CNB_PIPELINE_ID
        )
        return self.ctl.start_build(
            pipeline,
            {
                "BUILDER_IMAGE": self.bp.image,
                # 使用 base64 编码的 JSON 字符串，避免出现特殊符号传递失败的问题
                "ENV_VARS": base64.b64encode(json.dumps(env_vars).encode("utf-8")).decode("utf-8"),
            },
        )

    def _start_following_logs(self, pb: definitions.PipelineBuild):
        """通过轮询，检查流水线是否执行完成，并逐批获取执行日志"""
        time_started = time.time()

        while time.time() - time_started < _FOLLOWING_LOGS_TIMEOUT:
            time.sleep(self.FOLLOWING_LOGS_INTERVAL)
            self.stream.write_message("Devops pipeline is running, please wait patiently...")

            try:
                build_status = self.ctl.retrieve_build_status(pb)
            except BkDevopsGatewayServiceError:
                logger.exception(f"call devops pipeline for build status and logs failed during deploy[{self.bp}]")
                raise

            # 到达稳定状态后，可以退出轮询
            if build_status.status in [
                PipelineBuildStatus.SUCCEED,
                PipelineBuildStatus.FAILED,
                PipelineBuildStatus.CANCELED,
            ]:
                break

        # Q：为什么不在轮询过程中，按分块获取日志（做流式效果）
        # A：经测试，通过获取 log_num 再分块获取日志，会丢失部分日志，这是难以接受的，
        #    因此采用最后全量拉日志的方式，轮询过程中添加日志提示用户耐心等待流水线执行
        for log in self.ctl.retrieve_full_log(pb).logs:
            # 注：丢弃流水线/构建机启动相关日志，只保留构建组件的日志
            if log.tag.startswith("e-") and log.jobId.startswith("c-"):
                # 移除蓝盾日志中的级别 Tag，如 ##[error], ##[info] 等
                self.stream.write_message(re.sub(self.DEVOPS_LOG_LEVEL_TAG_REGEX, "", log.message))

    def _ensure_pipeline_build_success(self, pb: definitions.PipelineBuild) -> None:
        # 超时/结束轮询后，仍然不是成功状态，应抛出异常
        if self.ctl.retrieve_build_status(pb).status != PipelineBuildStatus.SUCCEED:
            raise DevopsPipelineBuildNotSuccess("build image with devops pipeline not success")

    def _create_and_bind_build_instance(self, metadata: Dict) -> Build:
        """
        创建 Build 对象并绑定到 BuildProcess 实例

        注：蓝盾流水线构建只支持镜像制品，不支持 slug 包
        """
        procfile = {}
        if "procfile" in metadata:
            procfile = metadata["procfile"]

        if "image" not in metadata:
            raise KeyError("metadata.image is required")

        build_inst = Build.objects.create(
            owner=self.deployment.operator,
            application_id=self.bp.application_id,
            module_id=self.bp.module_id,
            app=self.wl_app,
            slug_path=generate_slug_path(self.bp),
            image=metadata["image"],
            branch=self.bp.branch,
            revision=self.bp.revision,
            procfile=procfile,
            env_variables=generate_launcher_env_vars(slug_path=generate_slug_path(self.bp)),
            bkapp_revision_id=metadata.get("bkapp_revision_id", None),
            artifact_type=ArtifactType.IMAGE,
            artifact_metadata={
                "use_dockerfile": metadata.get("use_dockerfile", False),
                "use_cnb": metadata.get("use_cnb", False),
            },
        )
        mark_as_latest_artifact(build_inst)

        # retrieve bp object again, flush the status
        self.bp.build = build_inst
        self.bp.save(update_fields=["build"])
        self.bp.update_status(BuildStatus.SUCCESSFUL)
        return build_inst