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

from paasng.bk_plugins.pluginscenter.definitions import PluginBackendAPIResource
from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance, PluginRelease
from paasng.bk_plugins.pluginscenter.thirdparty import utils
from paasng.bk_plugins.pluginscenter.thirdparty.api_serializers import PluginReleaseAPIRequestSLZ

logger = logging.getLogger(__name__)


def callback_to_third_party(
    api_endpoint: Optional[PluginBackendAPIResource], instance: PluginInstance, version: PluginRelease, operator: str
) -> bool:
    """通用的回调第三方系统的函数，回调 API 未设置时，直接返回 True"""
    if not api_endpoint:
        logger.info("Callback API endpoint is not set, skip callback")
        return True

    slz = PluginReleaseAPIRequestSLZ(
        {
            "plugin_id": instance.id,
            "version": version,
            "operator": operator,
            "current_stage": version.current_stage,
            "status": version.status,
            "is_rolled_back": version.is_rolled_back,
            "latest_release_strategy": version.latest_release_strategy,
        }
    )
    data = slz.data
    resp = utils.make_client(api_endpoint).call(
        data=data, path_params={"plugin_id": instance.id, "version_id": version.id}
    )
    if not (result := resp.get("result", True)):
        logger.exception(f"Callback to {api_endpoint.apiName} failed: {resp}")
    return result


def create_release(pd: PluginDefinition, instance: PluginInstance, version: PluginRelease, operator: str) -> bool:
    """创建发布版本 - 回调第三方系统

    - 仅插件管理员声明了回调 API 时才会触发回调
    """
    release_definition = pd.get_release_revision_by_type(version.type)
    if not release_definition.api:
        logger.info("Callback API is not set, skip callback")
        return True
    return callback_to_third_party(release_definition.api.create, instance, version, operator)


def update_release(pd: PluginDefinition, instance: PluginInstance, version: PluginRelease, operator: str) -> bool:
    """版本发布结束时（状态：成功、失败、已中断） - 回调第三方系统

    - 仅插件管理员声明了回调 API 时才会触发回调
    """
    release_definition = pd.get_release_revision_by_type(version.type)
    if not release_definition.api:
        logger.info("Callback API is not set, skip callback")
        return True
    return callback_to_third_party(release_definition.api.update, instance, version, operator)


def rollback_release(pd: PluginDefinition, instance: PluginInstance, version: PluginRelease, operator: str) -> bool:
    """回滚版本时，回调第三方系统"""
    release_definition = pd.get_release_revision_by_type(version.type)
    if not release_definition.api:
        logger.info("Callback API is not set, skip callback")
        return True
    return callback_to_third_party(release_definition.api.rollback, instance, version, operator)
