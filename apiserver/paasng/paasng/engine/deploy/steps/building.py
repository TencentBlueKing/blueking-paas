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
from pathlib import Path
from typing import Optional

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, PollingResult, PollingStatus, TaskPoller
from blue_krill.redis_tools.messaging import StreamChannelSubscriber
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext as _

from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.dev_resources.sourcectl.utils import compress_directory, generate_temp_dir, generate_temp_file
from paasng.dev_resources.templates.constants import TemplateType
from paasng.dev_resources.templates.models import Template
from paasng.engine.configurations.config_var import get_env_variables
from paasng.engine.constants import BuildStatus, JobStatus
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.deploy.infra.output import Style
from paasng.engine.deploy.infra.source import (
    check_source_package,
    download_source_to_dir,
    get_app_description_handler,
    get_processes,
    get_source_package_path,
    tag_module_from_source_files,
)
from paasng.engine.deploy.steps.base import DeployPoller
from paasng.engine.deploy.steps.pre_release import ApplicationPreReleaseExecutor
from paasng.engine.deploy.workflow import (
    DeploymentCoordinator,
    DeploymentStateMgr,
    DeployProcedure,
    DeployStep,
    MessageParser,
    MessageStepMatcher,
)
from paasng.engine.models import Deployment
from paasng.engine.models.phases import DeployPhaseTypes
from paasng.engine.signals import post_phase_end, pre_appenv_build, pre_phase_start
from paasng.extensions.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.extensions.declarative.handlers import AppDescriptionHandler
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.core.storages.redisdb import get_default_redis
from paasng.platform.modules.models.module import Module
from paasng.utils.blobstore import make_blob_store

logger = logging.getLogger(__name__)


class ApplicationBuilder(DeployStep):
    """The main controller for building an application"""

    PHASE_TYPE = DeployPhaseTypes.BUILD

    @DeployStep.procedures
    def start(self):
        # Trigger signal
        pre_appenv_build.send(self.deployment.app_environment, deployment=self.deployment, step=self)
        try:
            self.handle_app_description()
        except FileNotFoundError:
            logger.debug("App description file not defined, do not process.")
        except DescriptionValidationError as e:
            self.stream.write_message(Style.Error(_("应用描述文件解析异常: {}").format(e.message)))
            logger.exception("Exception while parsing app description file, skip.")
        except ControllerError as e:
            self.stream.write_message(Style.Error(e.message))
            logger.exception("Exception while processing app description file, skip.")
        except Exception:
            self.stream.write_message(Style.Error(_("处理应用描述文件时出现异常, 请检查应用描述文件")))
            logger.exception("Exception while processing app description file, skip.")

        # TODO: 改造提示信息&错误信息都需要入库
        pre_phase_start.send(self, phase=DeployPhaseTypes.PREPARATION)
        preparation_phase = self.deployment.deployphase_set.get(type=DeployPhaseTypes.PREPARATION)
        relative_source_dir = self.deployment.get_source_dir()
        module = self.deployment.app_environment.module
        with self.procedure_force_phase(_('解析应用进程信息'), phase=preparation_phase):
            processes = get_processes(deployment=self.deployment, stream=self.stream)
            self.deployment.update_fields(procfile=processes)

        with self.procedure_force_phase(_('上传仓库代码'), phase=preparation_phase):
            source_destination_path = get_source_package_path(self.deployment)
            self.compress_and_upload(relative_source_dir, source_destination_path)

        with self.procedure_force_phase(_('配置资源实例'), phase=preparation_phase) as p:
            self._provision_services(p, module)

        # 由于准备阶段比较特殊，额外手动发送 phase end 消息
        post_phase_end.send(self, status=JobStatus.SUCCESSFUL, phase=DeployPhaseTypes.PREPARATION)

        pre_phase_start.send(self, phase=DeployPhaseTypes.BUILD)
        with self.procedure(_('启动应用构建任务')):
            self.async_start_build_process(source_destination_path, processes)

    def compress_and_upload(self, relative_source_dir: Path, source_destination_path: str):
        """Download, compress and upload module source files

        :param Path relative_source_dir: 源码目录(相对路径), 当源码目录不为 Path(".") 时, 表示仅打包上传 relative_source_dir 下的源码文件.
        :param str source_destination_path: 表示将源码归档包上传至对象存储中的位置.
        """
        module = self.deployment.app_environment.module
        with generate_temp_dir() as working_dir:
            source_dir = working_dir.absolute() / relative_source_dir
            download_source_to_dir(module, self.deployment.operator, self.deployment, working_dir)

            if not source_dir.exists():
                message = (
                    "The source directory '{source_dir}' does not exist,please check the repository to confirm."
                ).format(source_dir=str(relative_source_dir))
                self.stream.write_message(Style.Error(message))
                raise FileNotFoundError(message)
            if source_dir.is_file():
                message = _(
                    "The source directory '{source_dir}' is not a legal directory,please check repository to confirm."
                ).format(source_dir=str(relative_source_dir))
                self.stream.write_message(Style.Error(message))
                raise NotADirectoryError(message)

            tag_module_from_source_files(module, source_dir)
            with generate_temp_file(suffix='.tar.gz') as package_path:
                compress_directory(source_dir, package_path)
                check_source_package(self.engine_app, package_path, self.stream)
                logger.info(f"Uploading source files to {source_destination_path}")
                make_blob_store(bucket=settings.BLOBSTORE_BUCKET_APP_SOURCE).upload_file(
                    package_path, source_destination_path
                )

    def handle_app_description(self):
        """Handle application description for deployment"""
        module = self.deployment.app_environment.module
        application = module.application
        operator = self.deployment.operator
        version_info = self.deployment.version_info
        relative_source_dir = self.deployment.get_source_dir()

        if not application.feature_flag.has_feature(AppFeatureFlag.APPLICATION_DESCRIPTION):
            logger.debug("App description disabled.")
            return

        handler = get_app_description_handler(module, operator, version_info, relative_source_dir)
        if not handler:
            logger.debug("No valid app description file found.")
            return

        if not isinstance(handler, AppDescriptionHandler):
            logger.debug(
                "Currently only runtime configs such as environment variables declared in app_desc.yaml are applied."
            )
            return

        handler.handle_deployment(self.deployment)

    def async_start_build_process(self, source_tar_path, procfile):
        """Start a new build process and check the status periodically"""
        env_vars = get_env_variables(self.module_environment, deployment=self.deployment)
        build_process_id = self.engine_client.start_build_process(
            self.version_info, str(self.deployment.id), source_tar_path, procfile, env_vars
        )

        self.state_mgr.update(build_process_id=build_process_id)
        params = {"build_process_id": build_process_id, "deployment_id": self.deployment.id}
        BuildProcessPoller.start(params, BuildProcessResultHandler)

    def callback_build_process(self, build_process_id: str, result: dict):
        """Callback for a finished build process"""
        try:
            build_id = result['build_id']
            build_status = result['build_status']
        except KeyError:
            self.state_mgr.finish(JobStatus.FAILED, "An unexpected error occurred while building application")
            return

        self.state_mgr.update(build_id=build_id, build_status=build_status, build_process_id=build_process_id)
        if build_status == BuildStatus.FAILED:
            self.state_mgr.finish(JobStatus.FAILED, "Building failed, please check logs for more details")
        elif build_status == BuildStatus.INTERRUPTED:
            self.state_mgr.finish(JobStatus.INTERRUPTED, "Building interrupted")
        else:
            post_phase_end.send(self, status=JobStatus.SUCCESSFUL, phase=DeployPhaseTypes.BUILD)
            ApplicationPreReleaseExecutor.from_deployment_id(self.deployment.id).start()

    def _provision_services(self, p: DeployProcedure, module: Module):
        """Provision all preset services

        :param p: DeployProcedure object for writing hint messages
        :param module: Module to evaluate provision
        """
        self._notify_unexpected_missing_services(p, module)

        for rel in mixed_service_mgr.list_unprovisioned_rels(self.engine_app):
            p.stream.write_message(
                'Creating new service instance of %s, it will take several minutes...' % rel.get_service().display_name
            )
            rel.provision()

    def _notify_unexpected_missing_services(self, p: DeployProcedure, module: Module):
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


class BuildProcessPoller(DeployPoller):
    """Poller for querying the status of build process
    Finish when the building process in engine side was completed
    """

    max_retries_on_error = 10
    overall_timeout_seconds = 60 * 15
    default_retry_delay_seconds = 2

    @staticmethod
    def get_subscriber(channel_id) -> Optional[StreamChannelSubscriber]:
        subscriber = StreamChannelSubscriber(channel_id, redis_db=get_default_redis())
        channel_state = subscriber.get_channel_state()
        if channel_state == 'none':
            return None

        return subscriber

    def query(self) -> PollingResult:
        deployment = Deployment.objects.get(pk=self.params['deployment_id'])

        client = EngineDeployClient(deployment.get_engine_app())
        build_proc = client.get_build_process(self.params['build_process_id'])

        subscriber = self.get_subscriber(self.params['deployment_id'])
        phase = deployment.deployphase_set.get(type=DeployPhaseTypes.BUILD)
        pattern_maps = {
            JobStatus.PENDING: phase.get_started_pattern_map(),
            JobStatus.SUCCESSFUL: phase.get_finished_pattern_map(),
        }
        logger.info("[%s] going to get history events from redis", self.params['deployment_id'])
        if subscriber:
            for e in subscriber.get_history_events():
                event = MessageParser.parse_msg(e)
                if not event:
                    continue

                MessageStepMatcher.match_and_update_step(event, pattern_maps, phase)
        logger.info("[%s] history events from redis fetched", self.params['deployment_id'])

        build_status = build_proc.status
        build_id = str(build_proc.build_id) if build_proc.build_id else None

        status = PollingStatus.DOING
        if build_status in BuildStatus.get_finished_states():
            status = PollingStatus.DONE
        else:
            coordinator = DeploymentCoordinator(deployment.app_environment)
            # 若判断任务状态超时，则认为任务失败，否则更新上报状态时间
            if coordinator.status_polling_timeout:
                logger.warning(
                    "[deploy_id=%s, build_process_id=%s] polling build status timeout, regarding as failed by PaaS",
                    self.params["deployment_id"],
                    self.params["build_process_id"],
                )
                build_status = BuildStatus.FAILED
                status = PollingStatus.DONE
            else:
                coordinator.update_polling_time()

        result = {"build_id": build_id, "build_status": build_status}
        logger.info("[%s] got build status [%s][%s]", self.params['deployment_id'], build_id, build_status)
        return PollingResult(status=status, data=result)


class BuildProcessResultHandler(CallbackHandler):
    """Result handler for a finished build process"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        deployment_id = poller.params['deployment_id']
        state_mgr = DeploymentStateMgr.from_deployment_id(
            deployment_id=deployment_id, phase_type=DeployPhaseTypes.BUILD
        )

        if result.is_exception:
            state_mgr.finish(JobStatus.FAILED, "build process failed")
        else:
            build_process_id = poller.params['build_process_id']
            app_builder = ApplicationBuilder.from_deployment_id(deployment_id)
            app_builder.callback_build_process(build_process_id, result.data)


@shared_task
def start_build(deployment_id, *args, **kwargs):
    """Start a deployment process

    :param deployment_id: ID of deployment object
    """
    deploy_controller = ApplicationBuilder.from_deployment_id(deployment_id)
    deploy_controller.start()


@shared_task
def start_build_error_callback(*args, **kwargs):
    context = args[0]
    exc: Exception = args[1]
    # celery.worker.request.Request own property `args` after celery==4.4.0
    deployment_id = context._payload[0][0]

    state_mgr = DeploymentStateMgr.from_deployment_id(phase_type=DeployPhaseTypes.BUILD, deployment_id=deployment_id)
    state_mgr.finish(JobStatus.FAILED, str(exc), write_to_stream=False)
