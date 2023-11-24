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
from typing import Dict, Optional, Type, Union

import cattrs
import jinja2
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paasng.bk_plugins.pluginscenter import constants
from paasng.bk_plugins.pluginscenter.bk_devops import definitions as devops_definitions
from paasng.bk_plugins.pluginscenter.bk_devops.client import PipelineController
from paasng.bk_plugins.pluginscenter.bk_devops.constants import PipelineBuildStatus
from paasng.bk_plugins.pluginscenter.definitions import ReleaseStageDefinition, find_stage_by_id
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.itsm_adaptor.utils import get_ticket_status, submit_online_approval_ticket
from paasng.bk_plugins.pluginscenter.models import PluginReleaseStage
from paasng.bk_plugins.pluginscenter.serializers import ItsmTicketInfoSlz, PluginMarketInfoSLZ
from paasng.bk_plugins.pluginscenter.sourcectl import get_plugin_repo_accessor
from paasng.bk_plugins.pluginscenter.thirdparty import utils
from paasng.bk_plugins.pluginscenter.thirdparty.api_serializers import PluginBuildInfoSLZ
from paasng.bk_plugins.pluginscenter.thirdparty.deploy import check_deploy_result, deploy_version, get_deploy_logs
from paasng.bk_plugins.pluginscenter.thirdparty.market import read_market_info
from paasng.bk_plugins.pluginscenter.thirdparty.subpage import can_enter_next_stage

logger = logging.getLogger(__name__)


class BaseStageController:
    """发布步骤控制器基类"""

    _stage_types: Dict[constants.ReleaseStageInvokeMethod, Type["BaseStageController"]] = {}  # type: ignore
    invoke_method: constants.ReleaseStageInvokeMethod

    def __init__(self, stage: PluginReleaseStage):
        self.release = stage.release
        self.plugin = self.release.plugin
        self.pd = self.plugin.pd
        self.stage = stage

    def __init_subclass__(cls, **kwargs):
        # register subclass to stage_types dict
        cls._stage_types[cls.invoke_method] = cls

    @classmethod
    def get_stage_class(
        cls, invoke_method: Union[str, constants.ReleaseStageInvokeMethod]
    ) -> Type["BaseStageController"]:
        return cls._stage_types[constants.ReleaseStageInvokeMethod(invoke_method)]

    def execute(self, operator: str):
        """执行步骤"""
        raise NotImplementedError

    def render_to_view(self) -> Dict:
        """渲染发布阶段"""
        basic_info = {
            "stage_id": self.stage.stage_id,
            "stage_name": self.stage.stage_name,
            "status": self.stage.status,
            "fail_message": self.stage.fail_message,
        }
        return basic_info

    def async_check_status(self) -> bool:
        """异步检查执行状态, 用于 celery 任务
        :returns: return True if checker done, False to keep polling
        """
        return True


class DeployAPIStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.DEPLOY_API

    def execute(self, operator: str):
        if self.release.current_stage != self.stage:
            raise error_codes.EXECUTE_STAGE_ERROR.f(_("当前阶段并非部署阶段"))
        self._refresh_source_hash()

        current_stage = self.stage
        try:
            data = deploy_version(self.pd, self.plugin, self.release, operator)
            current_stage.status = constants.PluginReleaseStatus.PENDING
            current_stage.api_detail = data
            current_stage.save()
        except Exception as e:
            current_stage.update_status(constants.PluginReleaseStatus.FAILED, fail_message=str(e))
            raise

    def render_to_view(self) -> Dict:
        basic_info = super().render_to_view()
        if not self.stage.api_detail:
            # 部署步骤执行失败
            basic_info["status"] = constants.PluginReleaseStatus.FAILED
            return {
                **basic_info,
                "detail": {
                    "steps": [],
                    "finished": False,
                    "logs": [],
                },
            }
        # TODO: 在异步任务轮询查询部署结果
        check_deploy_result(self.pd, self.plugin, self.release)
        self.stage.refresh_from_db()
        return {
            **basic_info,
            "detail": {"steps": self.stage.api_detail["steps"], **get_deploy_logs(self.pd, self.plugin, self.release)},
        }

    def async_check_status(self):
        check_deploy_result(self.pd, self.plugin, self.release)
        self.stage.refresh_from_db()
        return self.stage.status not in constants.PluginReleaseStatus.running_status()

    def _refresh_source_hash(self):
        """刷新 source_hash 字段, 因为实际上部署以线上最新代码为准"""
        version_type = self.release.source_version_type
        version_name = self.release.source_version_name
        source_hash = get_plugin_repo_accessor(self.plugin).extract_smart_revision(f"{version_type}:{version_name}")
        if source_hash != self.release.source_hash:
            self.release.source_hash = source_hash
            self.release.save(update_fields=["source_hash", "updated"])


class ItsmStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.ITSM

    def execute(self, operator: str):
        submit_online_approval_ticket(self.pd, self.plugin, self.release, operator)

    def render_to_view(self) -> Dict:
        basic_info = super().render_to_view()
        assert self.stage.itsm_detail
        ticket_info = get_ticket_status(self.stage.itsm_detail.sn)
        ticket_info["fields"] = self.stage.itsm_detail.fields
        self.stage.refresh_from_db()
        return {
            **basic_info,
            "detail": ItsmTicketInfoSlz(ticket_info).data,
        }


class PipelineStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.PIPELINE

    def __init__(self, stage: PluginReleaseStage):
        super().__init__(stage)
        self.ctl = PipelineController(bk_username="admin")
        if stage.status == constants.PluginReleaseStatus.INITIAL or stage.pipeline_detail is None:
            self.build = None
        else:
            self.build = cattrs.structure(stage.pipeline_detail, devops_definitions.PipelineBuild)

    def render_to_view(self) -> Dict:
        if self.build is None:
            raise error_codes.STAGE_RENDER_ERROR.f(_("当前步骤状态异常"))
        basic_info = super().render_to_view()
        build_detail = self.ctl.retrieve_build_detail(self.build)
        # 如果已经构建完成，则主动更新当前步骤状态
        if build_detail.status not in constants.PluginReleaseStatus.running_status():
            self.async_check_status()
            self.stage.refresh_from_db()

        logs = self.ctl.retrieve_full_log(build=self.build).dict()
        return {**basic_info, "detail": build_detail.dict(), "logs": logs}

    def async_check_status(self) -> bool:
        if self.build is None:
            return False
        status = self.ctl.retrieve_build_status(build=self.build)
        if status.status == PipelineBuildStatus.SUCCEED:
            # 部分插件需要在构建成功后，回调第三方API来获取构建产物等
            is_success = self.execute_post_command()
            if not is_success:
                self.stage.update_status(
                    constants.PluginReleaseStatus.FAILED,
                    next((i.showMsg for i in status.stageStatus if i.showMsg), _("构建回调失败")),
                )
            else:
                self.stage.update_status(constants.PluginReleaseStatus.SUCCESSFUL)
        elif status.status == PipelineBuildStatus.FAILED:
            self.stage.update_status(
                constants.PluginReleaseStatus.FAILED,
                next((i.showMsg for i in status.stageStatus if i.showMsg), _("构建失败")),
            )
        elif status.status == PipelineBuildStatus.CANCELED:
            self.stage.update_status(
                constants.PluginReleaseStatus.INTERRUPTED,
                next((i.showMsg for i in status.stageStatus if i.showMsg), _("构建失败")),
            )
        return self.stage.status not in constants.PluginReleaseStatus.running_status()

    def execute(self, operator: str):
        stage_definition = find_stage_by_id(self.pd.release_stages, self.stage.stage_id)
        if stage_definition is None:
            raise error_codes.EXECUTE_STAGE_ERROR.f(_("当前步骤状态异常"))

        pipeline = devops_definitions.Pipeline(
            projectId=settings.PLUGIN_CENTER_PROJECT_ID, pipelineId=stage_definition.pipelineId
        )
        current_stage = self.stage
        try:
            build = self.ctl.start_build(pipeline=pipeline, start_params=self.build_pipeline_params(stage_definition))
            current_stage.status = constants.PluginReleaseStatus.PENDING
            current_stage.pipeline_detail = cattrs.unstructure(build)
            current_stage.save(update_fields=["status", "pipeline_detail"])
        except Exception as e:
            current_stage.update_status(constants.PluginReleaseStatus.FAILED, fail_message=str(e))
            raise

    def build_pipeline_params(self, stage_definition: ReleaseStageDefinition) -> Dict[str, str]:
        """渲染流水线插件参数"""
        if not stage_definition.pipelineParams:
            return {}
        context = {
            "pd_id": self.pd.identifier,
            "plugin_id": self.plugin.id,
            "release_id": self.release.id,
            "version": self.release.version,
            "comment": self.release.comment,
            "source_location": self.release.source_location,
            "source_version_type": self.release.source_version_type,
            "source_version_name": self.release.source_version_name,
            "source_hash": self.release.source_hash,
        }
        pipeline_params = {
            key: jinja2.Template(value).render(context) for key, value in stage_definition.pipelineParams.items()
        }
        return pipeline_params

    def execute_post_command(self) -> bool:
        """构建成功后执行后置命令 - 回调第三方系统

        - 仅插件定义中声明了回调 API 时才会触发回调
        """
        if self.build is None:
            return False

        stage_definition = find_stage_by_id(self.pd.release_stages, self.stage.stage_id)
        if stage_definition is None:
            raise error_codes.EXECUTE_STAGE_ERROR.f(_("当前步骤状态异常"))

        if not stage_definition.api or not stage_definition.api.postCommand:
            return True

        slz = PluginBuildInfoSLZ(
            {
                "pipeline_id": self.build.pipelineId,
                "build_id": self.build.buildId,
                "version": self.release.version,
                "version_with_underscores": self.release.version.replace(".", "_"),
                "bk_username": "admin",
            }
        )
        data = slz.data
        resp = utils.make_client(stage_definition.api.postCommand).call(
            data=data, path_params={"plugin_id": self.plugin.id}
        )
        if not (result := resp.get("result")):
            logger.error(f"execute post command [plugin_id: {self.plugin.id}, data:{data}], error: {resp}")
        return result


class SubPageStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.SUBPAGE

    def execute(self, operator: str):
        # 内嵌页面，不需要做任何处理
        return

    def render_to_view(self) -> Dict:
        basic_info = super().render_to_view()
        stage_def = find_stage_by_id(self.pd.release_stages, self.stage.stage_id)
        if not stage_def:
            raise error_codes.STAGE_DEF_NOT_FOUND

        page_url = self.format_page_url(stage_def)

        # 计算平台 UDC 插件，刷新页面时更新测试阶段状态，不做异步轮询
        can_proceed = can_enter_next_stage(self.pd, self.plugin, self.release)
        if can_proceed:
            self.stage.update_status(constants.PluginReleaseStatus.SUCCESSFUL)
        return {
            **basic_info,
            "detail": {
                "page_url": page_url,
                "can_proceed": can_proceed,
                "next_step_disabled_tips": stage_def.nextStepDisabledTips,
            },
        }

    def format_page_url(self, stage_def: ReleaseStageDefinition) -> Optional[str]:
        if page_url := stage_def.pageUrl:
            page_url = page_url.format(plugin_id=self.plugin.id, version_id=self.release.version)
        return page_url


class BuiltinStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.BUILTIN

    def execute(self, operator: str):
        if (
            self.stage.stage_id == "market"
            and self.pd.market_info_definition.storage == constants.MarketInfoStorageType.THIRD_PARTY
        ):
            # 对于市场信息只存储在第三方平台的插件, 该步骤只用于展示信息, 无需操作即可下一步
            self.stage.update_status(constants.PluginReleaseStatus.SUCCESSFUL)
        if self.stage.stage_id == "online":
            self.stage.update_status(constants.PluginReleaseStatus.SUCCESSFUL)

    def render_to_view(self) -> Dict:
        basic_info = super().render_to_view()
        if self.stage.stage_id == "market":
            market_info = self.plugin.pluginmarketinfo
            if self.pd.market_info_definition.storage == constants.MarketInfoStorageType.THIRD_PARTY:
                market_info = read_market_info(self.pd, self.plugin)
            return {
                **basic_info,
                "detail": PluginMarketInfoSLZ(market_info).data,
            }
        elif self.stage.stage_id == "grayScale":
            raise NotImplementedError
        elif self.stage.stage_id == "online":
            return {
                **basic_info,
                "detail": {
                    "status": "successful",
                    "message": _("插件已发布成功"),
                },
            }
        raise NotImplementedError


def init_stage_controller(stage: PluginReleaseStage) -> BaseStageController:
    return BaseStageController.get_stage_class(stage.invoke_method)(stage)
