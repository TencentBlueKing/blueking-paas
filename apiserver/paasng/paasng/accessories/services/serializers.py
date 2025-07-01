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

from paasng.accessories.services.models import PreCreatedInstance, Service


class PlanSlugField(serializers.SlugRelatedField):
    def get_queryset(self):
        svc: Service = self.context["service"]
        return svc.plan_set.filter(tenant_id=self.context["tenant_id"])


class PreCreatedInstanceImportSLZ(serializers.ModelSerializer):
    plan = PlanSlugField(slug_field="name")
    config = serializers.JSONField(help_text="same of ServiceInstance.config")
    credentials = serializers.JSONField(help_text="same of ServiceInstance.credentials")

    class Meta:
        model = PreCreatedInstance
        fields = "__all__"
