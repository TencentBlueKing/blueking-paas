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

from typing import Type

from rest_framework import serializers

from paasng.bk_plugins.pluginscenter.constants import PluginRole
from paasng.bk_plugins.pluginscenter.models import PluginDefinition
from paasng.bk_plugins.pluginscenter.serializers import make_plugin_slz_class
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.utils.i18n.serializers import i18n


def make_sys_plugin_slz_class(pd: PluginDefinition, creation: bool = False) -> Type[serializers.Serializer]:
    """创建插件的系统 API，需要添加创建者、租户等相关信息"""
    base_slz_class = make_plugin_slz_class(pd, creation)
    base_slz = base_slz_class()
    base_fields = base_slz.get_fields()

    # 继承基础序列化类的 Meta 信息
    meta_attrs = {}
    if hasattr(base_slz_class, "Meta"):
        meta_attrs = {k: v for k, v in base_slz_class.Meta.__dict__.items() if not k.startswith("_")}

    fields = {
        **base_fields,
        "creator": serializers.CharField(help_text="创建者", required=True),
        "repository": serializers.CharField(help_text="仓库地址", required=True),
        "plugin_tenant_id": serializers.CharField(
            help_text="租户ID，如租户类型为全租户，则 plugin_tenant_id 为空", default=""
        ),
        "tenant_id": serializers.CharField(
            help_text="插件所属租户，如租户类型为全租户，则 tenant_id 为 system", default=DEFAULT_TENANT_ID
        ),
        "Meta": type("Meta", (), meta_attrs),
    }
    return i18n(type("DynamicSysPluginSerializer", (serializers.Serializer,), fields))


class PluginRoleInputSLZ(serializers.Serializer):
    name = serializers.CharField(read_only=True, help_text="角色名称")
    id = serializers.ChoiceField(help_text="角色ID", choices=PluginRole.get_choices())


class PluginMemberInputSLZ(serializers.Serializer):
    username = serializers.CharField(help_text="用户名")
    role = PluginRoleInputSLZ(help_text="角色")
