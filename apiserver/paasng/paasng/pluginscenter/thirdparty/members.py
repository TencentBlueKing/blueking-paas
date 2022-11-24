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
from paasng.pluginscenter.iam_adaptor.management.shim import fetch_plugin_members
from paasng.pluginscenter.models import PluginDefinition, PluginInstance
from paasng.pluginscenter.thirdparty import utils
from paasng.pluginscenter.thirdparty.api_serializers import PluginMemberSLZ


def sync_members(pd: PluginDefinition, instance: PluginInstance):
    """同步插件开发中心成员列表至第三方系统"""
    slz = PluginMemberSLZ(fetch_plugin_members(plugin=instance), many=True)
    data = slz.data
    utils.make_client(pd.basic_info_definition.sync_members).call(data=data, path_params={"plugin_id": instance.id})
