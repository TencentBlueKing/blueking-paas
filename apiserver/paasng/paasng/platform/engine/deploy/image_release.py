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
from typing import Optional

from celery import shared_task
from django.utils.translation import gettext as _

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.cnative.specs.credentials import validate_references
from paas_wl.bk_app.cnative.specs.exceptions import InvalidImageCredentials
from paas_wl.workloads.images.models import AppImageCredential
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.bkapp_model.importer.exceptions import ManifestImportError
from paasng.platform.bkapp_model.manager import sync_to_bkapp_model
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.platform.declarative.handlers import AppDescriptionHandler, CNativeAppDescriptionHandler, PerformResult
from paasng.platform.engine.configurations.image import ImageCredentialManager, RuntimeImageInfo, get_credential_refs
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.deploy.release import start_release_step
from paasng.platform.engine.exceptions import DeployShouldAbortError
from paasng.platform.engine.models import Deployment, DeployPhaseTypes
from paasng.platform.engine.models.deployment import ProcessTmpl
from paasng.platform.engine.signals import post_phase_end, pre_phase_start
from paasng.platform.engine.utils.output import Style
from paasng.platform.engine.utils.source import get_app_description_handler, get_processes
from paasng.platform.engine.workflow import DeployProcedure, DeployStep
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

    phase_type = DeployPhaseTypes.RELEASE

    @DeployStep.procedures
    def start(self):
        if self.module_environment.application.type == ApplicationType.CLOUD_NATIVE.value:
            # 如果是云原生应用，更新 deployment 的 bkapp_revision_id
            bkapp_revision_id = self.create_bkapp_revision()
            self.deployment.update_fields(bkapp_revision_id=bkapp_revision_id)

        pre_phase_start.send(self, phase=DeployPhaseTypes.PREPARATION)
        preparation_phase = self.deployment.deployphase_set.get(type=DeployPhaseTypes.PREPARATION)

        module = self.module_environment.module
        is_smart_app = module.application.is_smart_app
        # DB 中存储的步骤名为中文，所以 procedure_force_phase 必须传中文，不能做国际化处理
        with self.procedure("解析应用进程信息", phase=preparation_phase):
            build_id = self.deployment.advanced_options.build_id
            if build_id:
                # 托管源码的应用在发布历史镜像时, advanced_options.build_id 不为空
                deployment: Deployment = (
                    Deployment.objects.filter(build_id=build_id).exclude(processes={}).order_by("-created").first()
                )
                if not deployment:
                    raise DeployShouldAbortError("failed to get processes")
                processes = deployment.get_processes()
                # 保存上一次部署的 Processes/Hooks 到 bkapp models
                # FIXME: sync_hooks 会重置 proc_command, 导致 proc_command 再次优先于 command/args 解析
                sync_to_bkapp_model(module=module, processes=processes, hooks=deployment.get_deploy_hooks())
            else:
                # advanced_options.build_id 为空有 2 种可能情况
                # 1. s-mart 应用
                # 2. 仅托管镜像的应用(包含云原生应用和旧镜像应用)
                use_cnb = False
                if is_smart_app:
                    # S-Mart 应用使用 S-Mart 包的元信息记录启动进程
                    perform_result = self.handle_smart_app_description()
                    if perform_result is not None:
                        proc_data_from_desc = perform_result.loaded_processes
                        use_cnb = perform_result.is_use_cnb()
                    processes = list(
                        get_processes(deployment=self.deployment, proc_data_from_desc=proc_data_from_desc).values()
                    )
                else:
                    processes = [
                        ProcessTmpl(
                            name=proc_spec.name,
                            command=proc_spec.get_proc_command(),
                            replicas=proc_spec.get_target_replicas(self.module_environment.environment),
                            plan=proc_spec.get_plan_name(self.module_environment.environment),
                            autoscaling=bool(proc_spec.get_autoscaling(self.module_environment.environment)),
                            scaling_config=proc_spec.get_scaling_config(self.module_environment.environment),
                            probes=proc_spec.probes,
                        )
                        for proc_spec in ModuleProcessSpec.objects.filter(module=module)
                    ]

                runtime_info = RuntimeImageInfo(engine_app=self.engine_app)
                # 目前构建流程必须 build_id, 因此需要构造 Build 对象
                build_id = self.engine_client.create_build(
                    image=runtime_info.generate_image(self.version_info),
                    extra_envs={"BKPAAS_IMAGE_APPLICATION_FLAG": "1"},
                    # 需要兼容 s-mart 应用
                    artifact_type=ArtifactType.SLUG if is_smart_app else ArtifactType.NONE,
                    artifact_metadata={
                        "use_cnb": use_cnb,
                    },
                )

            self.deployment.update_fields(
                processes={p.name: p for p in processes}, build_status=JobStatus.SUCCESSFUL, build_id=build_id
            )

        with self.procedure_force_phase("配置镜像访问凭证", phase=preparation_phase):
            self._setup_image_credentials()

        with self.procedure_force_phase("配置资源实例", phase=preparation_phase) as p:
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
                "Creating new service instance of %s, it will take several minutes..." % rel.get_service().display_name
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
            credential_refs = get_credential_refs(self.module_environment.module)
            if credential_refs:
                application = self.module_environment.application
                try:
                    validate_references(application, credential_refs)
                except InvalidImageCredentials as e:
                    # message = f"missing credentials {missing_names}"
                    self.stream.write_message(Style.Error(str(e)))
                    raise

                AppImageCredential.objects.flush_from_refs(application, self.engine_app.to_wl_obj(), credential_refs)

    def _handle_app_description(self) -> Optional[PerformResult]:
        """Handle application description for deployment"""
        module = self.deployment.app_environment.module
        handler = get_app_description_handler(module, self.deployment.operator, self.deployment.version_info)
        if not handler:
            logger.debug("No valid app description file found.")
            return None

        if not isinstance(handler, (AppDescriptionHandler, CNativeAppDescriptionHandler)):
            logger.debug(
                "Currently only runtime configs such as environment variables declared in app_desc.yaml are applied."
            )
            return None

        return handler.handle_deployment(self.deployment)

    def handle_smart_app_description(self) -> Optional[PerformResult]:
        """A tiny wrapper for _handle_app_description, will ignore all exception raise from _handle_app_description.
        And will do something for s-mart app

        - complete scripts command
        """
        result = None
        try:
            result = self._handle_app_description()
        except FileNotFoundError:
            logger.debug("App description file not defined, do not process.")
        except (DescriptionValidationError, ManifestImportError) as e:
            self.stream.write_message(Style.Error(_("应用描述文件解析异常: {}").format(e.message)))
            logger.exception("Exception while parsing app description file, skip.")
        except ControllerError as e:
            self.stream.write_message(Style.Error(e.message))
            logger.exception("Exception while processing app description file, skip.")
        except Exception:
            self.stream.write_message(Style.Error(_("处理应用描述文件时出现异常, 请检查应用描述文件")))
            logger.exception("Exception while processing app description file, skip.")

        return result
