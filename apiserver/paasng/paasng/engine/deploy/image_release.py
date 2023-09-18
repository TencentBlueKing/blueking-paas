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

from celery import shared_task
from django.utils.translation import gettext as _

from paas_wl.cnative.specs.credentials import get_references, validate_references
from paas_wl.cnative.specs.exceptions import InvalidImageCredentials
from paas_wl.cnative.specs.models import AppModelRevision
from paas_wl.platform.applications.constants import ArtifactType
from paas_wl.workloads.images.models import AppImageCredential
from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.engine.configurations.image import ImageCredentialManager, RuntimeImageInfo
from paasng.engine.constants import JobStatus
from paasng.engine.deploy.release import start_release_step
from paasng.engine.exceptions import DeployShouldAbortError
from paasng.engine.models import Deployment, DeployPhaseTypes
from paasng.engine.signals import post_phase_end, pre_phase_start
from paasng.engine.utils.output import Style
from paasng.engine.utils.source import get_app_description_handler, get_processes
from paasng.engine.workflow import DeployProcedure, DeployStep
from paasng.extensions.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.extensions.declarative.handlers import AppDescriptionHandler
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.modules.constants import SourceOrigin
from paasng.utils.i18n.celery import I18nTask

logger = logging.getLogger(__name__)


@shared_task(base=I18nTask)
def release_without_build(deployment_id, *args, **kwargs):
    """Skip the build and deploy the application directly

    :param deployment_id: ID of deployment object
    """
    deploy_controller = ImageReleaseMgr.from_deployment_id(deployment_id)
    deploy_controller.start()


class ImageReleaseMgr(DeployStep):
    """The main controller for release an Image application"""

    PHASE_TYPE = DeployPhaseTypes.RELEASE

    @DeployStep.procedures
    def start(self):
        pre_phase_start.send(self, phase=DeployPhaseTypes.PREPARATION)
        preparation_phase = self.deployment.deployphase_set.get(type=DeployPhaseTypes.PREPARATION)
        # DB 中存储的步骤名为中文，所以 procedure_force_phase 必须传中文，不能做国际化处理
        if self.module_environment.application.type != ApplicationType.CLOUD_NATIVE:
            self.try_handle_app_description()
            with self.procedure_force_phase('解析应用进程信息', phase=preparation_phase):
                build_id = self.deployment.advanced_options.build_id
                if not build_id:
                    # 旧的镜像应用从 deploy_config 读取进程信息
                    processes = get_processes(deployment=self.deployment)
                    # 旧的镜像应用需要构造 fake build
                    runtime_info = RuntimeImageInfo(engine_app=self.engine_app)
                    build_id = self.engine_client.create_build(
                        image=runtime_info.generate_image(self.version_info),
                        procfile={p.name: p.command for p in processes.values()},
                        extra_envs={"BKPAAS_IMAGE_APPLICATION_FLAG": "1"},
                        # 需要兼容 s-mart 应用
                        artifact_type=ArtifactType.SLUG
                        if self.module_environment.module.get_source_origin() == SourceOrigin.S_MART
                        else ArtifactType.NONE,
                    )
                else:
                    # TODO: 提供更好的处理方式, 不应该依赖上一个 Deployment
                    # Q: 为什么不从 Build.procfile 里读取?
                    # A: 因为 Build.procfile 目前只存储了启动命令, 没有 replicas/plan 等信息...
                    # 普通应用从第一个使用该 build 部署的 deployment 获取进程信息
                    deployment = (
                        Deployment.objects.filter(build_id=build_id).exclude(processes={}).order_by("-created").first()
                    )
                    if not deployment:
                        raise DeployShouldAbortError("failed to get processes")
                    processes = deployment.processes
                self.deployment.update_fields(
                    processes=processes, build_status=JobStatus.SUCCESSFUL, build_id=build_id
                )
        else:
            build_id = self.deployment.advanced_options.build_id
            if not build_id:
                # 仅托管镜像的云原生应用需要构造 fake build
                runtime_info = RuntimeImageInfo(engine_app=self.engine_app)
                build_id = self.engine_client.create_build(
                    image=runtime_info.generate_image(self.version_info),
                    procfile={},
                    extra_envs={},
                )
            self.deployment.update_fields(build_status=JobStatus.SUCCESSFUL, build_id=build_id)

        with self.procedure_force_phase('配置镜像访问凭证', phase=preparation_phase):
            self._setup_image_credentials()

        with self.procedure_force_phase('配置资源实例', phase=preparation_phase) as p:
            self._provision_services(p)

        # 由于准备阶段比较特殊，额外手动发送 phase end 消息
        post_phase_end.send(self, status=JobStatus.SUCCESSFUL, phase=DeployPhaseTypes.PREPARATION)
        start_release_step(deployment_id=self.deployment.id)

    def _provision_services(self, p: DeployProcedure):
        """Provision all preset services

        :param p: DeployProcedure object for writing hint messages
        """

        for rel in mixed_service_mgr.list_unprovisioned_rels(self.engine_app):
            p.stream.write_message(
                'Creating new service instance of %s, it will take several minutes...' % rel.get_service().display_name
            )
            rel.provision()

    def _setup_image_credentials(self):
        """Setup Image Credentials for pulling image"""
        if self.module_environment.application.type != ApplicationType.CLOUD_NATIVE:
            mgr = ImageCredentialManager(self.module_environment.module)
            credential = mgr.provide()
            # TODO: AppImageCredential.objects.flush_from_refs 移动到这里处理
            if credential:
                self.engine_client.upsert_image_credentials(
                    registry=credential.registry,
                    username=credential.username,
                    password=credential.password,
                )
        else:
            application = self.module_environment.application
            revision = AppModelRevision.objects.get(pk=self.deployment.bkapp_revision_id)
            try:
                credential_refs = get_references(revision.json_value)
                validate_references(application, credential_refs)
            except InvalidImageCredentials as e:
                # message = f"missing credentials {missing_names}"
                self.stream.write_message(Style.Error(str(e)))
                raise
            if credential_refs:
                AppImageCredential.objects.flush_from_refs(application, self.engine_app.to_wl_obj(), credential_refs)

    def _handle_app_description(self):
        """Handle application description for deployment"""
        module = self.deployment.app_environment.module
        handler = get_app_description_handler(module, self.deployment.operator, self.deployment.version_info)
        if not handler:
            logger.debug("No valid app description file found.")
            return

        if not isinstance(handler, AppDescriptionHandler):
            logger.debug(
                "Currently only runtime configs such as environment variables declared in app_desc.yaml are applied."
            )
            return

        handler.handle_deployment(self.deployment)

    def try_handle_app_description(self):
        """A tiny wrapper for _handle_app_description, will ignore all exception raise from _handle_app_description"""
        try:
            self._handle_app_description()
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
