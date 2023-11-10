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
from paasng.bk_plugins.pluginscenter.definitions import find_stage_by_id
from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance, PluginRelease
from paasng.bk_plugins.pluginscenter.thirdparty import utils


def can_enter_next_stage(pd: PluginDefinition, plugin: PluginInstance, version: PluginRelease):
    """获取子页面的状态，用于判断是否可进入到下一个页面"""
    current_stage = version.current_stage
    sub_stage_definition = find_stage_by_id(pd.release_stages, current_stage.stage_id)

    if not sub_stage_definition or not sub_stage_definition.api or not sub_stage_definition.api.result:
        raise ValueError("this plugin does not support get sub page result via API")

    resp = utils.make_client(sub_stage_definition.api.result).call(
        path_params={"plugin_id": plugin.id, "version_id": version.version}
    )
    # TODO 计算平台先给的临时 API，后续返回值为变
    status = resp.get('data', {}).get('status')
    return status == 'running'
