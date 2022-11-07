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
from typing import Dict, List

from paasng.pluginscenter.models import PluginDefinition, PluginInstance, PluginMarketInfo
from paasng.pluginscenter.thirdparty import utils
from paasng.pluginscenter.thirdparty.api_serializers import MarketCategorySLZ, PluginMarketRequestSLZ


def create_market_info(pd: PluginDefinition, instance: PluginInstance, market: PluginMarketInfo, operator: str):
    slz = PluginMarketRequestSLZ(market, context={"operator": operator})
    data = slz.data
    resp = utils.make_client(pd.market_info_definition.api.create).call(
        data=data, path_params={"plugin_id": instance.id}
    )
    return resp


def update_market_info(pd: PluginDefinition, instance: PluginInstance, market: PluginMarketInfo, operator: str):
    slz = PluginMarketRequestSLZ(market, context={"operator": operator})
    data = slz.data
    resp = utils.make_client(pd.market_info_definition.api.update).call(
        data=data, path_params={"plugin_id": instance.id}
    )
    return resp


def read_market_info(pd: PluginDefinition, instance: PluginInstance) -> PluginMarketInfo:
    resp = utils.make_client(pd.market_info_definition.api.read).call(path_params={"plugin_id": instance.id})
    slz = PluginMarketRequestSLZ(data=resp)
    slz.is_valid(raise_exception=True)
    data = slz.validated_data
    return PluginMarketInfo(plugin=instance, **data)


def list_category(pd: PluginDefinition) -> List[Dict]:
    resp = utils.make_client(pd.market_info_definition.category).call()
    slz = MarketCategorySLZ(data=resp, many=True)
    slz.is_valid(raise_exception=True)
    return slz.validated_data
