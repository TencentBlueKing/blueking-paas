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

"""Serializers for bk_plugins"""
from rest_framework import serializers

from .models import BkPluginDistributor, BkPluginProfile, BkPluginTag


class ListBkPluginsSLZ(serializers.Serializer):
    """Serializer for listing bk_plugins"""

    search_term = serializers.CharField(help_text="按名字或 code 过滤，默认不过滤", default="", required=False)
    has_deployed = serializers.BooleanField(
        help_text="按已部署状态过滤", default=None, required=False, allow_null=True
    )
    order_by = serializers.CharField(default="-created")
    distributor_code_name = serializers.CharField(help_text="按已授权使用方代号过滤", default=None, required=False)
    tag_id = serializers.IntegerField(
        help_text="按插件分类ID过滤, -1 代表过滤没有分类的插件", default=None, required=False
    )


class ListDetailedBkPluginsExtraSLZ(serializers.Serializer):
    """Extra serializer for listing detailed bk_plugins"""

    include_addresses = serializers.BooleanField(help_text="是否在结果中返回各环境访问地址", default=True)


class BkPluginSLZ(serializers.Serializer):
    """Serializer for representing bk_plugin"""

    id = serializers.CharField(read_only=True, help_text="插件 UUID（同应用 UUID）")
    region = serializers.CharField(read_only=True, help_text="插件所属 region")
    name = serializers.CharField(read_only=True, help_text="插件名称")
    code = serializers.CharField(read_only=True, help_text="插件 code")
    logo_url = serializers.CharField(read_only=True, help_text="插件的 Logo 地址")
    has_deployed = serializers.BooleanField(read_only=True, help_text="插件是否已经部署过")
    creator = serializers.CharField(read_only=True, help_text="插件创建者")
    created = serializers.DateTimeField(read_only=True, help_text="创建时间")
    updated = serializers.DateTimeField(read_only=True, help_text="更新时间")
    tag_info = serializers.DictField(read_only=True, help_text="插件分类信息")


class DeployedStatusSLZ(serializers.Serializer):
    deployed = serializers.BooleanField(read_only=True, help_text="是否已部署")
    addresses = serializers.JSONField(read_only=True, help_text="所有访问地址")


class DeployedStatusesSLZ(serializers.Serializer):
    # NOTE: deliberately hardcode environment name because client will depend on these values anyway
    stag = DeployedStatusSLZ()
    prod = DeployedStatusSLZ()


class ListBkPluginLogsSLZ(serializers.Serializer):
    trace_id = serializers.CharField(help_text="用于过滤日志的 trace_id 字段值", required=True)
    scroll_id = serializers.CharField(help_text="用于翻页的标志 ID", required=False)


class BkPluginProfileSLZ(serializers.ModelSerializer):
    """Serializer for representing and patching `BkPluginProfile`"""

    distributors = serializers.SlugRelatedField(
        help_text="插件使用方列表",
        slug_field="code_name",
        queryset=BkPluginDistributor.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = BkPluginProfile
        fields = [
            "introduction",
            "contact",
            "api_gw_name",
            "api_gw_id",
            "api_gw_last_synced_at",
            "tag",
            "distributors",
        ]


class BkPluginDetailedSLZ(serializers.Serializer):
    """Serializer for detailed bk_plugin object, with extra deployed statuses"""

    plugin = BkPluginSLZ()
    deployed_statuses = DeployedStatusesSLZ()
    profile = BkPluginProfileSLZ()


class DistributorSLZ(serializers.ModelSerializer):
    """Serializer for representing a plugin distributor"""

    class Meta:
        model = BkPluginDistributor
        fields = ["code_name", "name", "introduction"]


class UpdateDistributorsSLZ(serializers.Serializer):
    """Serializer for updating an plugin's distributors"""

    distributors = serializers.SlugRelatedField(
        help_text="插件使用方列表（代号）",
        slug_field="code_name",
        queryset=BkPluginDistributor.objects.all(),
        many=True,
    )


class BkPluginTagSLZ(serializers.ModelSerializer):
    """Serializer for representing a plugin tag"""

    class Meta:
        model = BkPluginTag
        fields = ["code_name", "name", "id", "priority"]
