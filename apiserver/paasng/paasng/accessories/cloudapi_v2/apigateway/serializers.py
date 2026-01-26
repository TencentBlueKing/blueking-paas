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

from paasng.accessories.cloudapi.constants import (
    ApplyStatusEnum,
    GrantDimensionEnum,
    PermissionApplyExpireDaysEnum,
)

# ============ 网关 API 相关 ============


class GatewayListQuerySLZ(serializers.Serializer):
    """获取网关列表请求参数"""

    name = serializers.CharField(help_text="搜索条件，支持模糊匹配网关名称或描述", required=False)
    fuzzy = serializers.BooleanField(help_text="是否模糊匹配", required=False, default=True)


class GatewayResourceListQuerySLZ(serializers.Serializer):
    """获取网关资源列表请求参数"""

    keyword = serializers.CharField(help_text="搜索条件，支持模糊匹配资源名称或描述", required=False)


class GatewayResourcePermissionApplySLZ(serializers.Serializer):
    """网关资源权限申请请求参数"""

    resource_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
        required=False,
        help_text="资源 ID 列表，不传则为网关维度申请",
    )
    reason = serializers.CharField(
        max_length=512,
        allow_blank=True,
        required=False,
        default="",
        help_text="申请原因",
    )
    expire_days = serializers.ChoiceField(
        choices=PermissionApplyExpireDaysEnum.get_django_choices(),
        help_text="过期天数",
    )
    grant_dimension = serializers.ChoiceField(
        choices=GrantDimensionEnum.get_django_choices(),
        help_text="授权维度：api-按网关，resource-按资源",
    )


class ResourcePermissionRenewSLZ(serializers.Serializer):
    """资源权限续期请求参数"""

    resource_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        required=True,
        help_text="资源 ID 列表",
    )
    expire_days = serializers.ChoiceField(
        choices=PermissionApplyExpireDaysEnum.get_django_choices(),
        help_text="过期天数",
    )


class PermissionApplyRecordQuerySLZ(serializers.Serializer):
    """权限申请记录查询请求参数"""

    applied_by = serializers.CharField(allow_blank=True, required=False, help_text="申请人")
    applied_time_start = serializers.IntegerField(
        allow_null=True, required=False, help_text="申请开始时间（Unix 时间戳）"
    )
    applied_time_end = serializers.IntegerField(
        allow_null=True, required=False, help_text="申请截止时间（Unix 时间戳）"
    )
    apply_status = serializers.ChoiceField(
        choices=ApplyStatusEnum.get_django_choices(),
        allow_blank=True,
        required=False,
        help_text="申请状态",
    )
    query = serializers.CharField(allow_blank=True, required=False, help_text="keyword")
    limit = serializers.IntegerField(default=10, required=False, help_text="分页大小")
    offset = serializers.IntegerField(default=0, required=False, help_text="分页偏移")


# ============ ESB 组件 API 相关 ============


class ESBSystemListQuerySLZ(serializers.Serializer):
    """查询组件系统列表请求参数"""

    keyword = serializers.CharField(help_text="搜索条件，支持模糊匹配系统名称或描述", required=False)


class ESBComponentListQuerySLZ(serializers.Serializer):
    """查询系统权限组件请求参数"""

    keyword = serializers.CharField(help_text="搜索条件，支持模糊匹配组件名称或描述", required=False)


class ESBComponentPermissionApplySLZ(serializers.Serializer):
    """ESB 组件权限申请请求参数"""

    component_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="组件 ID 列表",
    )
    reason = serializers.CharField(
        max_length=512,
        allow_blank=True,
        required=False,
        default="",
        help_text="申请原因",
    )
    expire_days = serializers.ChoiceField(
        choices=PermissionApplyExpireDaysEnum.get_django_choices(),
        help_text="过期天数",
    )


class ESBComponentPermissionRenewSLZ(serializers.Serializer):
    """ESB 组件权限续期请求参数"""

    component_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="组件 ID 列表",
    )
    expire_days = serializers.ChoiceField(
        choices=PermissionApplyExpireDaysEnum.get_django_choices(),
        help_text="过期天数",
    )
