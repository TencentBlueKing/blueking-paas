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

from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.engine.configurations.image import ImageCredentialManager
from paasng.engine.constants import JobStatus
from paasng.engine.deploy.bg_command.pre_release import ApplicationPreReleaseExecutor
from paasng.engine.models import DeployPhaseTypes
from paasng.engine.signals import post_phase_end, pre_phase_start
from paasng.engine.utils.output import Style
from paasng.engine.utils.source import get_app_description_handler, get_processes
from paasng.engine.workflow import DeployProcedure, DeployStep
from paasng.extensions.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.extensions.declarative.handlers import AppDescriptionHandler
from paasng.utils.i18n.celery import I18nTask

logger = logging.getLogger(__name__)


class ImageReleaseMgr(DeployStep):
    """The main controller for release an Image application"""

    PHASE_TYPE = DeployPhaseTypes.RELEASE

    @DeployStep.procedures
    def start(self):
        pre_phase_start.send(self, phase=DeployPhaseTypes.PREPARATION)
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

        preparation_phase = self.deployment.deployphase_set.get(type=DeployPhaseTypes.PREPARATION)
        with self.procedure_force_phase(_('解析应用进程信息'), phase=preparation_phase):
            processes = get_processes(deployment=self.deployment)
            build_id = self.engine_client.create_build(
                procfile={p.name: p.command for p in processes.values()},
                extra_envs={"BKPAAS_IMAGE_APPLICATION_FLAG": "1"},
            )
            self.deployment.update_fields(processes=processes, build_status=JobStatus.SUCCESSFUL, build_id=build_id)

        with self.procedure_force_phase(_('配置镜像访问凭证'), phase=preparation_phase):
            self._setup_image_credentials()

        with self.procedure_force_phase(_('配置资源实例'), phase=preparation_phase) as p:
            self._provision_services(p)

        # 由于准备阶段比较特殊，额外手动发送 phase end 消息
        post_phase_end.send(self, status=JobStatus.SUCCESSFUL, phase=DeployPhaseTypes.PREPARATION)

        # 执行部署前置命令
        ApplicationPreReleaseExecutor.from_deployment_id(self.deployment.id).start()

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
        mgr = ImageCredentialManager(self.module_environment.module)
        credential = mgr.provide()
        if credential:
            self.engine_client.upsert_image_credentials(
                registry=credential.registry,
                username=credential.username,
                password=credential.password,
            )

    def handle_app_description(self):
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


@shared_task(base=I18nTask)
def deploy_image(deployment_id, *args, **kwargs):
    """Start a deployment process

    :param deployment_id: ID of deployment object
    """
    deploy_controller = ImageReleaseMgr.from_deployment_id(deployment_id)
    deploy_controller.start()
