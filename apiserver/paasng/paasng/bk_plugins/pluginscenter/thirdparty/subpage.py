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

from paasng.bk_plugins.pluginscenter.definitions import find_stage_by_id
from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance, PluginRelease, PluginReleaseStage
from paasng.bk_plugins.pluginscenter.thirdparty import utils

logger = logging.getLogger(__name__)


def can_enter_next_stage(
    pd: PluginDefinition, plugin: PluginInstance, version: PluginRelease, stage: PluginReleaseStage
) -> bool:
    """获取子页面的状态，用于判断是否可进入到下一个页面"""
    sub_stage_definition = find_stage_by_id(pd, version, stage.stage_id)

    if not sub_stage_definition or not sub_stage_definition.api or not sub_stage_definition.api.result:
        raise ValueError("this plugin does not support get sub page result via API")

    resp = utils.make_client(sub_stage_definition.api.result).call(
        path_params={"plugin_id": plugin.id, "version_id": version.version}
    )
    if not resp.get("result", True):
        logger.error(f"get sub page status error: {resp.get('message')}")
        return False

    is_success = resp.get("data").get("is_success")
    return is_success
