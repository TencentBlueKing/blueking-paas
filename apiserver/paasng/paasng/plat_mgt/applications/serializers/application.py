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

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
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
        default_quotas = {"memory": "--", "cpu": "--"}
        if app_resource_quotas := self.context.get("app_resource_quotas"):
            return app_resource_quotas.get(instance.code, default_quotas)
        return default_quotas

    class Meta:
        model = Application
        fields = (
            "logo_url",
            "code",
            "name",
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
