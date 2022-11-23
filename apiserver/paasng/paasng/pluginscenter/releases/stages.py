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
from typing import Dict, Type, Union

from paasng.pluginscenter import constants
from paasng.pluginscenter.definitions import find_stage_by_id
from paasng.pluginscenter.exceptions import error_codes
from paasng.pluginscenter.itsm_adaptor.utils import get_ticket_status, submit_online_approval_ticket
from paasng.pluginscenter.models import PluginReleaseStage
from paasng.pluginscenter.serializers import ItsmTicketInfoSlz, PluginMarketInfoSLZ
from paasng.pluginscenter.thirdparty.deploy import check_deploy_result, deploy_version, get_deploy_logs
from paasng.pluginscenter.thirdparty.market import read_market_info


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


class DeployAPIStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.DEPLOY_API

    def execute(self, operator: str):
        deploy_version(self.pd, self.plugin, self.release, operator)

    def render_to_view(self) -> Dict:
        basic_info = super().render_to_view()
        # TODO: 在异步任务轮询查询部署结果
        check_deploy_result(self.pd, self.plugin, self.release)
        self.stage.refresh_from_db()
        return {
            **basic_info,
            "detail": {"steps": self.stage.api_detail["steps"], **get_deploy_logs(self.pd, self.plugin, self.release)},
        }


class ItsmStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.ITSM

    def execute(self, operator: str):
        submit_online_approval_ticket(self.pd, self.plugin, self.release, operator)

    def render_to_view(self) -> Dict:
        basic_info = super().render_to_view()
        assert self.stage.itsm_detail
        ticket_info = get_ticket_status(self.stage.itsm_detail.sn)
        ticket_info['fields'] = self.stage.itsm_detail.fields
        return {
            **basic_info,
            "detail": ItsmTicketInfoSlz(ticket_info).data,
        }


class PipelineStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.PIPELINE

    def execute(self, operator: str):
        raise NotImplementedError


class SubPageStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.SUBPAGE

    def execute(self, operator: str):
        raise NotImplementedError

    def render_to_view(self) -> Dict:
        basic_info = super().render_to_view()
        stage_def = find_stage_by_id(self.pd.release_stages, self.stage.stage_id)
        if not stage_def:
            raise error_codes.STAGE_DEF_NOT_FOUND
        return {**basic_info, "detail": {"page_url": stage_def.pageUrl}}


class BuiltinStage(BaseStageController):
    invoke_method = constants.ReleaseStageInvokeMethod.BUILTIN

    def execute(self, operator: str):
        if (
            self.stage.stage_id == "market"
            and self.pd.market_info_definition.storage == constants.MarketInfoStorageType.THIRD_PARTY
        ):
            # 对于市场信息只存储在第三方平台的插件, 该步骤只用于展示信息, 无需操作即可下一步
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
            raise NotImplementedError
        raise NotImplementedError


def init_stage_controller(stage: PluginReleaseStage) -> BaseStageController:
    return BaseStageController.get_stage_class(stage.invoke_method)(stage)
