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


class BaseMCPServerQueryParamsSLZ(serializers.Serializer):
    limit = serializers.IntegerField(help_text="最大返回条目数", required=False)
    offset = serializers.IntegerField(help_text="相对于完整未分页数据的起始位置", required=False)


class MCPServerQueryParamsSLZ(BaseMCPServerQueryParamsSLZ):
    """获取 mcp_server 列表请求参数"""

    keyword = serializers.CharField(help_text="搜索条件，支持模糊匹配 MCPServer 名称或描述", required=False)


class AppMCPServerPermissionQueryParamsSLZ(BaseMCPServerQueryParamsSLZ):
    """获取 app mcp_server 权限列表请求参数"""


class AppMCPServerPermissionApplyRecordQueryParamsSLZ(BaseMCPServerQueryParamsSLZ):
    """获取指定应用的 mcp_server 权限申请记录列表"""

    mcp_server_id = serializers.IntegerField(help_text="mcp_server_ids", required=False)


class ApplyMCPResourcePermissionSLZ(serializers.Serializer):
    """申请 mcp_resource 权限请求参数"""

    mcp_server_ids = serializers.ListField(child=serializers.IntegerField(), help_text="mcp_server ID 列表")
    applied_by = serializers.CharField(help_text="申请人")
    reason = serializers.CharField(help_text="申请原因")
    gateway_name = serializers.CharField(help_text="网关名称，用于记录操作记录")
