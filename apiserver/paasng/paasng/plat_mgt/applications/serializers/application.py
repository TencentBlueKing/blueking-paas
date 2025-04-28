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

from paasng.core.core.storages.redisdb import DefaultRediStore
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.applications.tasks import cal_app_resource_quotas
from paasng.utils.serializers import HumanizeDateTimeField, UserNameField


class ApplicationSLZ(serializers.ModelSerializer):
    """应用序列化器"""

    logo_url = serializers.CharField(read_only=True, source="get_logo_url", help_text="应用的Logo地址")
    app_type = serializers.SerializerMethodField(read_only=True)
    resource_quotas = serializers.SerializerMethodField(read_only=True)

    creator = UserNameField()
    created_humanized = HumanizeDateTimeField(source="created")

    def get_app_type(self, instance: Application) -> str:
        return ApplicationType.get_choice_label(instance.type)

    def get_resource_quotas(self, instance: Application) -> dict:
        """获取应用资源配额, 优先从 Redis 缓存获取, 缺失时触发异步任务计算"""
        default_quotas = {"memory": "--", "cpu": "--"}

        # 尝试从 Redis 中获取资源配额
        store = DefaultRediStore(rkey="quotas::app")
        app_resource_quotas = store.get()

        # 如果 Redis 中没有数据，触发异步任务计算
        if not app_resource_quotas:
            cal_app_resource_quotas.delay()
            return default_quotas

        return app_resource_quotas.get(instance.code, default_quotas)

    class Meta:
        model = Application
        fields = (
            "logo_url",
            "code",
            "name",
            "app_tenant_id",
            "app_tenant_mode",
            "app_type",
            "resource_quotas",
            "is_active",
            "creator",
            "created_humanized",
        )


class ApplicationDetailSLZ(ApplicationSLZ):
    """应用详细信息序列化器"""

    updated_humanized = HumanizeDateTimeField(source="updated")

    class Meta:
        model = Application
        fields = "__all__"


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
