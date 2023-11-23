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

from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance
from paasng.bk_plugins.pluginscenter.thirdparty import utils

logger = logging.getLogger(__name__)


def sync_config(pd: PluginDefinition, instance: PluginInstance):
    """同步插件开发者中心-插件配置至第三方系统"""
    if pd.config_definition is None:
        raise ValueError("this plugin does not support configuration feature")
    data = [config.row for config in instance.configs.all()]
    resp = utils.make_client(pd.config_definition.sync_api).call(data=data, path_params={"plugin_id": instance.id})

    if not (result := resp.get("result")):
        logger.error(f"sync config error [plugin_id: {instance.id}, data:{data}], error: {resp}")
    return result
