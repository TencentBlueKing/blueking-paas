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
from rest_framework import serializers

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.applications.models.managers.app_metadata import get_metadata
from paas_wl.bk_app.processes.drf_serializers import HumanizeDateTimeField, InstanceForDisplaySLZ
from paas_wl.bk_app.processes.models import ProcessSpecPlan


class ProcessSpecBoundInfoSLZ(serializers.Serializer):
    id = serializers.CharField()
    app_code = serializers.SerializerMethodField()
    target_replicas = serializers.CharField(help_text="目标副本数")
    target_status = serializers.CharField(help_text="用户设置的目标状态")

    def get_app_code(self, data) -> str:
        wl_app = WlApp.objects.get(pk=data.engine_app_id)
        return get_metadata(wl_app).get_paas_app_code()


class ProcessSpecPlanSLZ(serializers.ModelSerializer):
    created_humanized = HumanizeDateTimeField(source="created", read_only=True)
    updated_humanized = HumanizeDateTimeField(source="updated", read_only=True)
    limits = serializers.JSONField()
    requests = serializers.JSONField()
    instance_cnt = serializers.SerializerMethodField(help_text="使用该 plan 的 ProcessSpec 数量")

    def get_instance_cnt(self, obj):
        return obj.processspec_set.count()

    class Meta:
        model = ProcessSpecPlan
        fields = '__all__'


class InstanceSerializer(InstanceForDisplaySLZ):
    envs = serializers.DictField(child=serializers.CharField(), help_text="环境变量", required=False, default=dict)
