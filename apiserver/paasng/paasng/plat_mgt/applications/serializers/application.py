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

from paasng.core.tenant.constants import AppTenantMode
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.utils.models import OrderByField
from paasng.utils.serializers import HumanizeDateTimeField, UserNameField


class ApplicationSLZ(serializers.Serializer):
    """应用序列化器"""

    logo = serializers.CharField(read_only=True, help_text="应用 logo")
    code = serializers.CharField(read_only=True, help_text="应用的唯一标识")
    name = serializers.CharField(read_only=True, help_text="应用名称")
    app_tenant_id = serializers.CharField(read_only=True, help_text="应用租户 ID")
    app_tenant_mode = serializers.CharField(read_only=True, help_text="应用租户模式")
    type = serializers.SerializerMethodField(read_only=True)
    resource_quotas = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.BooleanField(read_only=True, help_text="应用是否处于激活状态")
    creator = UserNameField()
    created_humanized = HumanizeDateTimeField(source="created")

    def get_type(self, instance: Application) -> str:
        return ApplicationType.get_choice_label(instance.type)

    def get_resource_quotas(self, instance: Application) -> dict:
        """从 context 中获取应用的资源配额"""
        default_quotas = {"memory": "--", "cpu": "--"}
        app_resource_quotas = self.context.get("app_resource_quotas")

        if not app_resource_quotas:
            return default_quotas

        return app_resource_quotas.get(instance.code, default_quotas)


class ApplicationDetailSLZ(ApplicationSLZ):
    """应用详细信息序列化器"""

    owner = UserNameField()
    language = serializers.CharField(read_only=True, help_text="应用语言")
    last_deployed_date = serializers.DateTimeField(read_only=True, help_text="最后部署时间")
    is_smart_app = serializers.BooleanField(read_only=True, help_text="是否 smart 应用")

    updated_humanized = HumanizeDateTimeField(source="updated")


class ApplicationFilterSLZ(serializers.Serializer):
    """应用列表过滤器序列化器"""

    valid_order_by_fields = ("is_active", "created")

    search = serializers.CharField(required=False, help_text="应用名称/ID 关键字搜索")
    name = serializers.CharField(required=False, help_text="应用名称")
    app_tenant_id = serializers.CharField(required=False, help_text="应用租户 ID")
    app_tenant_mode = serializers.ChoiceField(
        required=False,
        choices=AppTenantMode.get_choices(),
        help_text="应用租户模式",
    )
    type = serializers.ChoiceField(
        required=False,
        choices=ApplicationType.get_choices(),
        help_text="应用类型",
    )
    is_active = serializers.BooleanField(
        required=False,
        allow_null=True,
        help_text="应用状态: true(正常) / false(下架), null 或不传表示不进行过滤",
    )
    order_by = serializers.ListField(default=["-created", "is_active"], help_text="排序字段")

    def validate_order_by(self, fields) -> list:
        """校验排序字段"""
        for field in fields:
            f = OrderByField.from_string(field)
            if f.name not in self.valid_order_by_fields:
                raise serializers.ValidationError(f"Invalid order_by field: {field}")
        return fields


class TenantIdListSLZ(serializers.Serializer):
    """租户 ID 列表序列化器"""

    tenant_id = serializers.CharField(help_text="租户 ID")
    app_count = serializers.IntegerField(help_text="应用数量")


class TenantModeListSLZ(serializers.Serializer):
    """租户模式列表序列化器"""

    type = serializers.CharField(help_text="租户模式")
    label = serializers.CharField(help_text="租户模式标签")


class ApplicationTypeListSLZ(serializers.Serializer):
    """应用类型列表序列化器"""

    type = serializers.CharField(help_text="应用类型")
    label = serializers.CharField(help_text="应用类型标签")
