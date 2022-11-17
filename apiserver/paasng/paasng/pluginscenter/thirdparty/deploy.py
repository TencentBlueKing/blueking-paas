"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import Dict

from paasng.pluginscenter.constants import PluginReleaseStatus, ReleaseStageInvokeMethod
from paasng.pluginscenter.definitions import find_stage_by_id
from paasng.pluginscenter.models import PluginDefinition, PluginInstance, PluginRelease
from paasng.pluginscenter.thirdparty import utils
from paasng.pluginscenter.thirdparty.api_serializers import (
    DeployPluginRequestSLZ,
    PluginDeployResponseSLZ,
    PluginReleaseLogsResponseSLZ,
)


def deploy_version(pd: PluginDefinition, plugin: PluginInstance, version: PluginRelease, operator: str):
    """调用第三方系统 API 触发版本发布/部署"""
    current_stage = version.current_stage
    if not current_stage or current_stage.invoke_method != ReleaseStageInvokeMethod.DEPLOY_API:
        raise ValueError("this version is not ready to deploy")
    if current_stage.status != PluginReleaseStatus.INITIAL:
        raise ValueError("unable to re-deploy a deployed version")

    deploy_stage_definition = find_stage_by_id(pd.release_stages, current_stage.stage_id)
    if not deploy_stage_definition or not deploy_stage_definition.api or not deploy_stage_definition.api.release:
        raise ValueError("this plugin does not support deploy via API")

    request_slz = DeployPluginRequestSLZ({"plugin_id": plugin.id, "version": version, "operator": operator})
    resp = utils.make_client(deploy_stage_definition.api.release).call(
        data=request_slz.data, path_params={"plugin_id": plugin.id}
    )
    response_slz = PluginDeployResponseSLZ(data=resp)
    response_slz.is_valid(raise_exception=True)
    data = response_slz.validated_data

    current_stage.status = PluginReleaseStatus.PENDING
    current_stage.api_detail = data
    current_stage.save()


def check_deploy_result(pd: PluginDefinition, plugin: PluginInstance, version: PluginRelease) -> PluginReleaseStatus:
    """查询第三方系统的发布/部署结果"""
    current_stage = version.current_stage
    if not current_stage or current_stage.invoke_method != ReleaseStageInvokeMethod.DEPLOY_API:
        raise ValueError("this version is not ready to deploy")
    if current_stage.status == PluginReleaseStatus.INITIAL:
        raise ValueError("unable to retrieve results of unstarted deploy")

    deploy_stage_definition = find_stage_by_id(pd.release_stages, current_stage.stage_id)
    if not deploy_stage_definition or not deploy_stage_definition.api or not deploy_stage_definition.api.result:
        raise ValueError("this plugin does not support deploy via API")

    resp = utils.make_client(deploy_stage_definition.api.result).call(
        path_params={"plugin_id": plugin.id, "deploy_id": current_stage.api_detail["deploy_id"]}
    )
    response_slz = PluginDeployResponseSLZ(data=resp)
    response_slz.is_valid(raise_exception=True)
    data = response_slz.validated_data

    current_stage.api_detail = data
    status = PluginReleaseStatus(data["status"])
    if status in PluginReleaseStatus.abnormal_status():
        current_stage.update_status(status, fail_message=data["detail"])
    elif status == PluginReleaseStatus.SUCCESSFUL:
        current_stage.update_status(status)
    return status


def get_deploy_logs(pd: PluginDefinition, plugin: PluginInstance, version: PluginRelease) -> Dict:
    """查询部署日志"""
    current_stage = version.current_stage
    if not current_stage or current_stage.invoke_method != ReleaseStageInvokeMethod.DEPLOY_API:
        raise ValueError("this version is not ready to deploy")
    if current_stage.status == PluginReleaseStatus.INITIAL:
        raise ValueError("unable to retrieve logs of unstarted deploy")

    deploy_stage_definition = find_stage_by_id(pd.release_stages, current_stage.stage_id)
    if not deploy_stage_definition or not deploy_stage_definition.api or not deploy_stage_definition.api.log:
        raise ValueError("this plugin does not support deploy via API")

    resp = utils.make_client(deploy_stage_definition.api.log).call(
        path_params={"plugin_id": plugin.id, "deploy_id": current_stage.api_detail["deploy_id"]}
    )
    response_slz = PluginReleaseLogsResponseSLZ(data=resp)
    response_slz.is_valid(raise_exception=True)
    return response_slz.validated_data
