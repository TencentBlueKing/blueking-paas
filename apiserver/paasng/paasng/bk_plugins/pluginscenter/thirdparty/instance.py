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

from paasng.bk_plugins.pluginscenter.constants import PluginStatus
from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance
from paasng.bk_plugins.pluginscenter.thirdparty import utils
from paasng.bk_plugins.pluginscenter.thirdparty.api_serializers import (
    PluginRequestCreateSLZ,
    PluginRequestSLZ,
    PluginVisibleRangeAPIRequestSLZ,
)

logger = logging.getLogger(__name__)


def create_instance(pd: PluginDefinition, instance: PluginInstance, operator: str) -> bool:
    slz = PluginRequestCreateSLZ(instance, context={"operator": operator})
    data = slz.data
    resp = utils.make_client(pd.basic_info_definition.api.create).call(data=data)
    if not (result := resp.get("result", True)):
        logger.error(f"create instance error [operator: {operator}, data:{data}], error: {resp}")
    return result


def update_instance(pd: PluginDefinition, instance: PluginInstance, operator: str) -> bool:
    slz = PluginRequestSLZ(instance, context={"operator": operator})
    data = slz.data
    resp = utils.make_client(pd.basic_info_definition.api.update).call(
        data=data, path_params={"plugin_id": instance.id}
    )
    if not (result := resp.get("result", True)):
        logger.error(f"upadte instance error [plugin_id: {instance.id}, data:{data}], error: {resp}")
    return result


def archive_instance(pd: PluginDefinition, instance: PluginInstance, operator: str) -> bool:
    resp = utils.make_client(pd.basic_info_definition.api.delete).call(
        path_params={"plugin_id": instance.id}, data={"operator": operator}
    )
    if not resp.get("result", True):
        logger.error(f"archive instance error [plugin_id: {instance.id}], error: {resp}")
        return False

    instance.status = PluginStatus.ARCHIVED
    instance.save(update_fields=["status", "updated"])
    return True


def reactivate_instance(pd: PluginDefinition, instance: PluginInstance, operator: str) -> bool:
    if not pd.basic_info_definition.api.reactivate:
        return True

    resp = utils.make_client(pd.basic_info_definition.api.reactivate).call(
        path_params={"plugin_id": instance.id}, data={"operator": operator}
    )
    if not resp.get("result", True):
        logger.error(f"archive instance error [plugin_id: {instance.id}], error: {resp}")
        return False

    instance.status = PluginStatus.DEVELOPING
    instance.save(update_fields=["status", "updated"])
    return True


def visible_range_callback(pd: PluginDefinition, instance: PluginInstance, operator: str) -> bool:
    """可见范围修改审批成功时 - 回调第三系统

    - 仅插件管理员声明了回调 API 时才会触发回调
    """
    if not pd.visible_range_definition.api.update:
        logger.info("Visible range update callback API not configured, skipping callback")
        return True

    if not hasattr(instance, "visible_range"):
        logger.info(f"The plugin (id: {instance.id}) has not set the visible range, skipping callback")
        return True

    slz = PluginVisibleRangeAPIRequestSLZ(
        {
            "plugin_id": instance.id,
            "operator": operator,
            "bkci_project": instance.visible_range.bkci_project,
            "organization": instance.visible_range.organization,
        }
    )
    data = slz.data
    resp = utils.make_client(pd.visible_range_definition.api.update).call(
        data=data, path_params={"plugin_id": instance.id}
    )
    if not (result := resp.get("result", True)):
        logger.error(f"create release error: {resp}")
    return result
