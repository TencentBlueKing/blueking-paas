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
import logging

from django.utils.translation import gettext as _

from paasng.dev_resources.sourcectl.git.client import GitCommandExecutionError
from paasng.pluginscenter import constants
from paasng.pluginscenter.definitions import find_stage_by_id
from paasng.pluginscenter.exceptions import error_codes
from paasng.pluginscenter.models import PluginInstance, PluginMarketInfo, PluginMembership, PluginReleaseStage
from paasng.pluginscenter.serializers import PluginMarketInfoSLZ
from paasng.pluginscenter.sourcectl import get_plugin_repo_initializer
from paasng.pluginscenter.sourcectl.exceptions import APIError
from paasng.pluginscenter.thirdparty.deploy import check_deploy_result, deploy_version, get_deploy_logs
from paasng.pluginscenter.thirdparty.instance import create_instance
from paasng.pluginscenter.thirdparty.market import read_market_info

logger = logging.getLogger(__name__)


def init_plugin_in_view(plugin: PluginInstance, operator: str):
    if plugin.pd.basic_info_definition.release_method == constants.PluginReleaseMethod.CODE:
        init_plugin_repository(plugin)

    if plugin.pd.basic_info_definition.api.create:
        try:
            create_instance(plugin.pd, plugin, operator)
        except Exception:
            logger.exception("同步插件信息至第三方系统失败, 请联系相应的平台管理员排查")
            raise error_codes.THIRD_PARTY_API_ERROR
    # 创建者默认是管理员
    PluginMembership.objects.create(plugin=plugin, role=constants.PluginRole.ADMINISTRATOR, user=operator)
    # 创建默认市场信息
    PluginMarketInfo.objects.create(plugin=plugin, extra_fields={})


def init_plugin_repository(plugin: PluginInstance):
    """初始化插件仓库"""
    initializer = get_plugin_repo_initializer(plugin.pd)
    try:
        initializer.create_project(plugin)
    except APIError as e:
        logger.exception("创建仓库返回异常, 异常信息: %s", e.message)
        raise error_codes.CREATE_REPO_ERROR

    try:
        initializer.initial_repo(plugin)
    except GitCommandExecutionError:
        logger.exception("执行 git 指令异常, 请联系管理员排查")
        raise error_codes.INITIAL_REPO_ERROR


def build_repository_template(repository_group: str) -> str:
    """transfer a repository group to repository template"""
    if not repository_group.endswith("/"):
        repository_group += "/"
    return repository_group + "{{ plugin_id }}.git"


def render_release_stage(stage: PluginReleaseStage):
    """渲染发布阶段"""
    release = stage.release
    plugin = stage.release.plugin
    pd = stage.release.plugin.pd
    basic_info = {
        "stage_id": stage.stage_id,
        "stage_name": stage.stage_name,
        "status": stage.status,
        "fail_message": stage.fail_message,
    }
    if stage.invoke_method == constants.ReleaseStageInvokeMethod.DEPLOY_API:
        # TODO: 在异步任务轮询查询部署结果
        check_deploy_result(pd, plugin, release)
        return {
            **basic_info,
            "detail": {"steps": stage.api_detail["steps"], **get_deploy_logs(pd, plugin, release)},
        }
    elif stage.invoke_method == constants.ReleaseStageInvokeMethod.BUILTIN:
        if stage.stage_id == "market":
            pd = stage.release.plugin.pd
            market_info = plugin.pluginmarketinfo
            if pd.market_info_definition.storage == constants.MarketInfoStorageType.THIRD_PARTY:
                market_info = read_market_info(pd, plugin)
            return {
                **basic_info,
                "detail": PluginMarketInfoSLZ(market_info).data,
            }
        elif stage.stage_id == "grayScale":
            raise NotImplementedError
        elif stage.stage_id == "online":
            raise NotImplementedError
    elif stage.invoke_method == constants.ReleaseStageInvokeMethod.ITSM:
        raise NotImplementedError
    elif stage.invoke_method == constants.ReleaseStageInvokeMethod.PIPELINE:
        raise NotImplementedError
    elif stage.invoke_method == constants.ReleaseStageInvokeMethod.SUBPAGE:
        stage_def = find_stage_by_id(pd.release_stages, stage.stage_id)
        if not stage_def:
            raise error_codes.STAGE_DEF_NOT_FOUND
        return {**basic_info, "detail": {"page_url": stage_def.pageUrl}}
    raise NotImplementedError


def execute_stage(stage: PluginReleaseStage, operator: str):
    """执行阶段"""
    release = stage.release
    plugin = stage.release.plugin
    pd = stage.release.plugin.pd
    stage.status = constants.PluginReleaseStatus.PENDING
    if stage.invoke_method == constants.ReleaseStageInvokeMethod.DEPLOY_API:
        deploy_version(pd, plugin, release, operator)
    elif stage.invoke_method == constants.ReleaseStageInvokeMethod.ITSM:
        raise NotImplementedError
    elif stage.invoke_method == constants.ReleaseStageInvokeMethod.PIPELINE:
        raise NotImplementedError
    elif stage.invoke_method == constants.ReleaseStageInvokeMethod.BUILTIN:
        if (
            stage.stage_id == "market"
            and pd.market_info_definition.storage == constants.MarketInfoStorageType.THIRD_PARTY
        ):
            # 对于市场信息只存储在第三方平台的插件, 该步骤只用于展示信息, 无需操作即可下一步
            stage.status = constants.PluginReleaseStatus.SUCCESSFUL
        return stage.save()


def enter_next_stage(stage: PluginReleaseStage, operator: str):
    """进入下一个发布阶段"""
    if stage.status != constants.PluginReleaseStatus.SUCCESSFUL:
        raise error_codes.EXECUTE_STAGE_ERROR.f(_("当前阶段未执行成功, 不允许进入下一阶段"))
    next_stage = stage.next_stage
    if next_stage is None:
        # TODO: 怎样描述「确认上线」这个操作, 是否需要调用第三方平台的接口呢？
        # - 标准运维插件不需要，接入其他类型插件再考虑该情况
        release = stage.release
        release.current_stage = None
        release.status = constants.PluginReleaseStatus.SUCCESSFUL
        release.save()
        return

    if next_stage.status != constants.PluginReleaseStatus.INITIAL:
        raise error_codes.EXECUTE_STAGE_ERROR.f(_("下一阶段已被执行, 不能重复触发已执行的阶段"))

    release = stage.release
    release.current_stage = next_stage
    release.save()
    execute_stage(next_stage, operator)
