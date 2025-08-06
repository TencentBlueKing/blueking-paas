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

from rest_framework import serializers

from paasng.accessories.cloudapi_v2.constants import PermissionApplyStatus


class MCPServerQueryParamsSLZ(serializers.Serializer):
    """获取 mcp_server 列表请求参数"""

    keyword = serializers.CharField(help_text="搜索条件，支持模糊匹配 MCPServer 名称或描述", required=False)


class AppMCPServerPermissionApplyRecordQueryParamsSLZ(serializers.Serializer):
    """获取指定应用的 mcp_server 权限申请记录列表"""

    applied_by = serializers.CharField(help_text="申请人", required=False)
    applied_time_start = serializers.IntegerField(help_text="申请开始时间（Unix 时间戳）", required=False)
    applied_time_end = serializers.IntegerField(help_text="申请截止时间（Unix 时间戳）", required=False)
    apply_status = serializers.ChoiceField(
        choices=PermissionApplyStatus.get_django_choices(),
        required=False,
    )
    query = serializers.CharField(help_text="搜索条件，支持模糊匹配 MCPServer 名称", required=False)


class ApplyMCPResourcePermissionInputSLZ(serializers.Serializer):
    """申请 mcp_resource 权限请求参数"""

    mcp_server_ids = serializers.ListField(child=serializers.IntegerField(), help_text="mcp_server ID 列表")
    applied_by = serializers.CharField(help_text="申请人")
    reason = serializers.CharField(help_text="申请原因")
