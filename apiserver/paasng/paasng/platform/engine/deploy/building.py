# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import logging
import time
from typing import Optional

import cattr
from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, PollingResult, PollingStatus, TaskPoller
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext as _

from paas_wl.bk_app.applications.entities import BuildMetadata
from paas_wl.bk_app.applications.models.build import BuildProcess
from paas_wl.bk_app.cnative.specs.models import AppModelResource
from paas_wl.infras.cluster.utils import get_image_registry_by_app
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ApplicationEnvironment
from paasng.platform.bkapp_model.exceptions import ManifestImportError
from paasng.platform.bkapp_model.manifest import get_bkapp_resource
from paasng.platform.bkapp_model.services import upsert_proc_svc_by_spec_version
from paasng.platform.declarative.deployment.controller import DeployHandleResult
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.engine.configurations.building import (
    SlugbuilderInfo,
    get_build_args,
    get_dockerfile_path,
    get_use_bk_ci_pipeline,
)
from paasng.platform.engine.configurations.config_var import get_env_variables
from paasng.platform.engine.configurations.image import (
    RuntimeImageInfo,
    generate_image_repository_by_env,
)
from paasng.platform.engine.constants import BuildStatus, JobStatus, RuntimeType
from paasng.platform.engine.deploy.base import DeployPoller
from paasng.platform.engine.deploy.bg_build.bg_build import start_bg_build_process
from paasng.platform.engine.deploy.release import start_release_step
from paasng.platform.engine.exceptions import HandleAppDescriptionError, InitDeployDescHandlerError
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.models.phases import DeployPhaseTypes
from paasng.platform.engine.phases_steps.steps import update_step_by_line
from paasng.platform.engine.signals import post_phase_end, pre_appenv_build, pre_phase_start
from paasng.platform.engine.utils.output import Style
from paasng.platform.engine.utils.source import (
    check_source_package,
    download_source_to_dir,
    get_deploy_desc_handler_by_version,
    get_dockerignore,
    get_source_package_path,
    tag_module_from_source_files,
)
from paasng.platform.engine.workflow import DeploymentCoordinator, DeploymentStateMgr, DeployProcedure, DeployStep
from paasng.platform.modules.models.module import Module
from paasng.platform.sourcectl.utils import (
    ExcludeChecker,
    compress_directory_ext,
    generate_temp_dir,
    generate_temp_file,
)
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.utils.blobstore import make_blob_store
from paasng.utils.i18n.celery import I18nTask

logger = logging.getLogger(__name__)


@shared_task(base=I18nTask)
def start_build(deployment_id, runtime_type: RuntimeType, *args, **kwargs):
    """Start a deployment process

    :param deployment_id: ID of deployment object
    :param runtime_type: runtime type of Application
    """
    if runtime_type == RuntimeType.BUILDPACK:
        deploy_controller = ApplicationBuilder.from_deployment_id(deployment_id)
    elif runtime_type == RuntimeType.DOCKERFILE:
        deploy_controller = DockerBuilder.from_deployment_id(deployment_id)
    else:
        raise NotImplementedError
    deploy_controller.start()


@shared_task(base=I18nTask)
def start_build_error_callback(*args, **kwargs):
    context = args[0]
    exc: Exception = args[1]
    # celery.worker.request.Request own property `args` after celery==4.4.0
    deployment_id = context._payload[0][0]

    state_mgr = DeploymentStateMgr.from_deployment_id(phase_type=DeployPhaseTypes.BUILD, deployment_id=deployment_id)
    state_mgr.finish(JobStatus.FAILED, str(exc), write_to_stream=False)


class BaseBuilder(DeployStep):
    phase_type = DeployPhaseTypes.BUILD

    def compress_and_upload(self, source_destination_path: str, should_ignore: Optional[ExcludeChecker] = None):
        """Download, compress and upload module source files

        :param str source_destination_path: 表示将源码归档包上传至对象存储中的位置.
        """
        module = self.deployment.app_environment.module
        with generate_temp_dir() as working_dir:
            try:
                _, source_dir = download_source_to_dir(module, self.deployment.operator, self.deployment, working_dir)
            except ValueError as e:
                self.stream.write_message(Style.Error(str(e)))
                raise

            tag_module_from_source_files(module, source_dir)
            with generate_temp_file(suffix=".tar.gz") as package_path:
                compress_directory_ext(source_dir, package_path, should_ignore=should_ignore)
                check_source_package(self.engine_app, package_path, self.stream)
                logger.info(f"Uploading source files to {source_destination_path}")
                make_blob_store(bucket=settings.BLOBSTORE_BUCKET_APP_SOURCE).upload_file(
                    package_path, source_destination_path
                )

    def handle_app_description(self) -> DeployHandleResult:
        """Handle the description files for deployment. It try to parse the app description
        file and store the related configurations, e.g. processes.
        Set the implicit_needed flag for process services at the end.

        :raises HandleAppDescriptionError: When failed to handle the app description.
        """
        try:
            app_environment = self.deployment.app_environment
            handler = get_deploy_desc_handler_by_version(
                app_environment.module,
                self.deployment.operator,
                self.deployment.version_info,
                self.deployment.get_source_dir(),
            )
            result = handler.handle(self.deployment)

            upsert_proc_svc_by_spec_version(app_environment.module, result.spec_version)
        except InitDeployDescHandlerError as e:
            raise HandleAppDescriptionError(reason=_("处理应用描述文件失败：{}".format(e)))
        except (DescriptionValidationError, ManifestImportError) as e:
            raise HandleAppDescriptionError(reason=_("应用描述文件解析异常: {}").format(e.message)) from e
        except Exception as e:
            logger.exception("Error while handling app description file, deployment: %s.", self.deployment)
            raise HandleAppDescriptionError(reason=_("处理应用描述文件时出现异常, 请检查应用描述文件")) from e
        else:
            return result

    def create_bkapp_revision(self) -> int:
        """generate bkapp model and store it into AppModelResource for querying the deployed bkapp model"""
        module = self.module_environment.module
        application = module.application
        bkapp = get_bkapp_resource(module=module)

        # Get current module resource object
        model_resource = AppModelResource.objects.get(application_id=application.id, module_id=module.id)
        model_resource.use_resource(bkapp)
        # 从源码部署总是使用最新创建的 revision
        return model_resource.revision.id

    def provision_services(self, p: DeployProcedure, module: Module):
        """Provision all preset services

        :param p: DeployProcedure object for writing hint messages
        :param module: Module to evaluate provision
        """
        self.notify_unexpected_missing_services(p, module)

        for rel in mixed_service_mgr.list_unprovisioned_rels(self.engine_app):
            p.stream.write_message(
                "Creating new service instance of %s, it will take several minutes..." % rel.get_service().display_name
            )
            rel.provision()

    def notify_unexpected_missing_services(self, p: DeployProcedure, module: Module):
        """Find services which should be bound but not bound, display warning messages"""
        try:
            tmpl = Template.objects.get(name=module.source_init_template, type=TemplateType.NORMAL)
        except ObjectDoesNotExist:
            return

        # Find services which SHOULD have be bound but unbound yet
        preset_service_names = set(tmpl.preset_services_config.keys())
        bound_service_names = {service_obj.name for service_obj in mixed_service_mgr.list_binded(module)}
        unbound_service_names = preset_service_names - bound_service_names
        if unbound_service_names:
            message = _(
                "The predefined Add-ons {unbound_service_names} in the initial template are not enabled, "
                "please check if they need to be enabled"
            ).format(unbound_service_names=unbound_service_names)
            self.stream.write_message(Style.Warning(message))

    def async_start_build_process(self, source_tar_path: str, bkapp_revision_id: Optional[int] = None):
        """Start a new build process and check the status periodically"""
        build_process_id = self.launch_build_processes(
            source_tar_path,
            bkapp_revision_id,
        )
        self.state_mgr.update(build_process_id=build_process_id)
        params = {"build_process_id": build_process_id, "deployment_id": self.deployment.id}
        BuildProcessPoller.start(params, BuildProcessResultHandler)

    def launch_build_processes(self, source_tar_path: str, bkapp_revision_id: Optional[int] = None):
        raise NotImplementedError


class ApplicationBuilder(BaseBuilder):
    """The main controller for building an application via Buildpack"""

    @DeployStep.procedures
    def start(self):
        # Trigger signal
        pre_appenv_build.send(self.deployment.app_environment, deployment=self.deployment, step=self)

        # TODO: 改造提示信息&错误信息都需要入库
        pre_phase_start.send(self, phase=DeployPhaseTypes.PREPARATION)
        preparation_phase = self.deployment.deployphase_set.get(type=DeployPhaseTypes.PREPARATION)
        module = self.deployment.app_environment.module

        is_cnative_app = self.module_environment.application.type == ApplicationType.CLOUD_NATIVE
        # DB 中存储的步骤名为中文，所以 procedure_force_phase 必须传中文，不能做国际化处理
        with self.procedure_force_phase("解析应用进程信息", phase=preparation_phase):
            self.handle_app_description()

        bkapp_revision_id = None
        if is_cnative_app:
            with self.procedure_force_phase("生成应用模型", phase=preparation_phase):
                bkapp_revision_id = self.create_bkapp_revision()
                self.deployment.update_fields(bkapp_revision_id=bkapp_revision_id)

        with self.procedure_force_phase("上传仓库代码", phase=preparation_phase):
            source_destination_path = get_source_package_path(self.deployment)
            self.compress_and_upload(source_destination_path)

        with self.procedure_force_phase("配置资源实例", phase=preparation_phase) as p:
            self.provision_services(p, module)

        # 由于准备阶段比较特殊，额外手动发送 phase end 消息
        post_phase_end.send(self, status=JobStatus.SUCCESSFUL, phase=DeployPhaseTypes.PREPARATION)

        pre_phase_start.send(self, phase=DeployPhaseTypes.BUILD)
        with self.procedure("启动应用构建任务"):
            self.async_start_build_process(
                source_tar_path=source_destination_path,
                bkapp_revision_id=bkapp_revision_id,
            )

    def launch_build_processes(self, source_tar_path: str, bkapp_revision_id: Optional[int] = None):
        """Start a new build process[using Buildpack], this will start a celery task in the background without
        blocking current process.
        """
        env = self.deployment.app_environment
        extra_envs = get_env_variables(env)

        # get slugbuilder and buildpacks from engine_app
        build_info = SlugbuilderInfo.from_engine_app(env.get_engine_app())
        runtime_info = RuntimeImageInfo(env.get_engine_app())
        # 注入构建环境所需环境变量
        extra_envs = {**extra_envs, **build_info.environments}

        # Use the default image when it's None, which means no images are bound to the app
        builder_image = build_info.build_image or settings.DEFAULT_SLUGBUILDER_IMAGE

        app_image_repository = generate_image_repository_by_env(env)
        app_image = runtime_info.generate_image(
            version_info=self.version_info, special_tag=self.deployment.advanced_options.special_tag
        )
        # Create the Build object and start a background build task
        build_process = BuildProcess.objects.new(
            owner=self.deployment.operator,
            env=env,
            builder_image=builder_image,
            source_tar_path=source_tar_path,
            version_info=self.version_info,
            invoke_message=self.deployment.advanced_options.invoke_message or _("发布时自动构建"),
            buildpacks_info=build_info.buildpacks_info,
        )

        # Start the background build process
        build_metadata = BuildMetadata(
            image=app_image,
            use_cnb=build_info.use_cnb,
            image_repository=app_image_repository,
            buildpacks=build_process.buildpacks_as_build_env(),
            extra_envs=extra_envs,
            bkapp_revision_id=bkapp_revision_id,
        )

        start_bg_build_process.delay(
            self.deployment.id,
            build_process.uuid,
            metadata=cattr.unstructure(build_metadata),
            stream_channel_id=str(self.deployment.id),
            use_bk_ci_pipeline=get_use_bk_ci_pipeline(env.module),
        )
        return str(build_process.uuid)


class DockerBuilder(BaseBuilder):
    """The main controller for building an image via Dockerfile"""

    @DeployStep.procedures
    def start(self):
        # Trigger signal
        pre_appenv_build.send(self.deployment.app_environment, deployment=self.deployment, step=self)

        pre_phase_start.send(self, phase=DeployPhaseTypes.PREPARATION)
        preparation_phase = self.deployment.deployphase_set.get(type=DeployPhaseTypes.PREPARATION)
        module: Module = self.deployment.app_environment.module

        is_cnative_app = self.module_environment.application.type == ApplicationType.CLOUD_NATIVE
        # DB 中存储的步骤名为中文，所以 procedure_force_phase 必须传中文，不能做国际化处理
        with self.procedure_force_phase("解析应用进程信息", phase=preparation_phase):
            self.handle_app_description()

        bkapp_revision_id = None
        if is_cnative_app:
            with self.procedure_force_phase("生成应用模型", phase=preparation_phase):
                bkapp_revision_id = self.create_bkapp_revision()
                self.deployment.update_fields(bkapp_revision_id=bkapp_revision_id)

        with self.procedure_force_phase("解析 .dockerignore", phase=preparation_phase):
            # 此处尝试读取项目 .dockerignore 文件，并将其内容传递到 compress_and_upload -> compress_directory_ext
            # 函数中，以求在二次打包源码包时，忽略掉 ignore 文件中所定义的文件和目录。但是，这么做的原因并非出于
            # 功能性——后续由其他组件负责的镜像打包过程（如 kaniko）也会妥善处置 ignore 文件，而是出于压缩包大
            # 小以及性能方面（具体的优化程度待测试）的考虑。
            #
            # 但是，当前整个 .dockerignore 文件的处理逻辑（DockerIgnore / patternmacher.Pattern），实际有着
            # 比较高的复杂度，其中大部分代码逻辑重写自 moby 的 Go 源码，所以，考虑到收益并不明确/突出的前提
            # 下，保留目前解析 .dockerignore 和处理的逻辑实际上比较奢侈。
            #
            # 综上所述，未来可能：
            #
            # 1. 删除：完全删掉 apiserver 中对 .dockerignore 文件的支持和相关代码，不寻求缩小压缩包；
            # 2. 保留但简化实现：采用 docker-py 库中的相关实现（PatternMatcher），来替代目前实现。
            #
            dockerignore = get_dockerignore(deployment=self.deployment)

        with self.procedure_force_phase("上传仓库代码", phase=preparation_phase):
            source_destination_path = get_source_package_path(self.deployment)
            self.compress_and_upload(
                source_destination_path, should_ignore=dockerignore.should_ignore if dockerignore else None
            )

        with self.procedure_force_phase("配置资源实例", phase=preparation_phase) as p:
            self.provision_services(p, module)

        # 由于准备阶段比较特殊，额外手动发送 phase end 消息
        post_phase_end.send(self, status=JobStatus.SUCCESSFUL, phase=DeployPhaseTypes.PREPARATION)

        pre_phase_start.send(self, phase=DeployPhaseTypes.BUILD)
        with self.procedure("启动应用构建任务"):
            self.async_start_build_process(
                source_tar_path=source_destination_path,
                bkapp_revision_id=bkapp_revision_id,
            )

    def launch_build_processes(self, source_tar_path: str, bkapp_revision_id: Optional[int] = None):
        """Start a new build process[using Dockerfile], this will start a celery task in the background without
        blocking current process.
        """
        env: ApplicationEnvironment = self.deployment.app_environment
        builder_image = settings.KANIKO_IMAGE
        app_image_repository = generate_image_repository_by_env(env)
        app_image = RuntimeImageInfo(env.get_engine_app()).generate_image(
            version_info=self.version_info, special_tag=self.deployment.advanced_options.special_tag
        )

        image_registry = get_image_registry_by_app(env.wl_app)
        # 注入构建环境所需环境变量
        extra_envs = {
            "DOCKERFILE_PATH": get_dockerfile_path(env.module),
            "BUILD_ARG": get_build_args(env.module),
            "REGISTRY_MIRRORS": settings.KANIKO_REGISTRY_MIRRORS,
            "SKIP_TLS_VERIFY_REGISTRIES": image_registry.host if image_registry.skip_tls_verify else "",
        }

        # Create the Build object and start a background build task
        build_process = BuildProcess.objects.new(
            owner=self.deployment.operator,
            env=env,
            builder_image=builder_image,
            source_tar_path=source_tar_path,
            version_info=self.version_info,
            invoke_message=self.deployment.advanced_options.invoke_message or _("发布时自动构建"),
        )

        build_metadata = BuildMetadata(
            image=app_image,
            image_repository=app_image_repository,
            use_dockerfile=True,
            extra_envs=extra_envs,
            bkapp_revision_id=bkapp_revision_id,
        )

        # Start the background build process
        start_bg_build_process.delay(
            self.deployment.id,
            build_process.uuid,
            metadata=cattr.unstructure(build_metadata),
            stream_channel_id=str(self.deployment.id),
            use_bk_ci_pipeline=get_use_bk_ci_pipeline(env.module),
        )
        return str(build_process.uuid)


class BuildProcessPoller(DeployPoller):
    """Poller for querying the status of build process
    Finish when the building process in engine side was completed
    """

    max_retries_on_error = 10
    overall_timeout_seconds = settings.BUILD_PROCESS_TIMEOUT
    default_retry_delay_seconds = 2

    def query(self) -> PollingResult:
        deployment = Deployment.objects.get(pk=self.params["deployment_id"])
        build_proc = BuildProcess.objects.get(pk=self.params["build_process_id"])

        self.update_steps(deployment, build_proc)

        build_status = build_proc.status
        build_id = str(build_proc.build_id) if build_proc.build_id else None

        status = PollingStatus.DOING
        if build_status in BuildStatus.get_finished_states():
            status = PollingStatus.DONE
        else:
            coordinator = DeploymentCoordinator(deployment.app_environment)
            # 若判断任务状态超时，则认为任务失败，否则更新上报状态时间
            if coordinator.is_status_polling_timeout:
                logger.warning(
                    "Polling status of build process [%s] timed out, consider it failed, deployment: %s",
                    self.params["build_process_id"],
                    self.params["deployment_id"],
                )
                build_status = BuildStatus.FAILED
                status = PollingStatus.DONE
            else:
                coordinator.update_polling_time()

        result = {"build_id": build_id, "build_status": build_status}
        logger.info(
            'The status of build process [%s] is "%s", deployment: %s, build_id: %s',
            self.params["build_process_id"],
            build_status,
            self.params["deployment_id"],
            build_id,
        )
        return PollingResult(status=status, data=result)

    def update_steps(self, deployment: Deployment, build_proc: BuildProcess):
        """Update deploy steps by processing all log lines of build process."""
        # Update deploy steps by log line
        phase = deployment.deployphase_set.get(type=DeployPhaseTypes.BUILD)
        pattern_maps = {
            JobStatus.PENDING: phase.get_started_pattern_map(),
            JobStatus.SUCCESSFUL: phase.get_finished_pattern_map(),
        }
        started_at = time.time()
        logger.info("Update deployment steps by log lines, deployment: %s", self.params["deployment_id"])

        # TODO: Use a flag value to indicate the progress of the scanning of the log,
        # so that we won't need to scan the log from the beginning every time.
        for line in build_proc.output_stream.lines.all().values_list("line", flat=True):
            update_step_by_line(line, pattern_maps, phase)

        logger.info(
            "Finished updating deployment steps, deployment: %s, cost: %s",
            self.params["deployment_id"],
            time.time() - started_at,
        )


class BuildProcessResultHandler(CallbackHandler):
    """Result handler for a finished build process"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        """Callback for a finished build process"""
        build_process_id = poller.params["build_process_id"]
        deployment_id = poller.params["deployment_id"]
        state_mgr = DeploymentStateMgr.from_deployment_id(
            deployment_id=deployment_id, phase_type=DeployPhaseTypes.BUILD
        )

        if result.is_exception:
            state_mgr.finish(JobStatus.FAILED, "build process failed")
            return

        try:
            build_id = result.data["build_id"]
            build_status = result.data["build_status"]
        except KeyError:
            state_mgr.finish(JobStatus.FAILED, "An unexpected error occurred while building application")
            return

        state_mgr.update(build_id=build_id, build_status=build_status, build_process_id=build_process_id)
        if build_status == BuildStatus.FAILED:
            state_mgr.finish(JobStatus.FAILED, "Building failed, please check logs for more details")
        elif build_status == BuildStatus.INTERRUPTED:
            state_mgr.finish(JobStatus.INTERRUPTED, "Building interrupted")
        else:
            post_phase_end.send(state_mgr, status=JobStatus.SUCCESSFUL, phase=DeployPhaseTypes.BUILD)
            start_release_step(deployment_id)
