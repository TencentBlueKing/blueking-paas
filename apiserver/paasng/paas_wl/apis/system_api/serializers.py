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
import re

from rest_framework import serializers

from paas_wl.bk_app.monitoring.metrics.constants import MetricsSeriesType
from paas_wl.bk_app.processes.kres_entities import Instance

# proc type name is alphanumeric
# https://docs-v2.readthedocs.io/en/latest/using-workflow/process-types-and-the-procfile/#declaring-process-types
PROCTYPE_MATCH = re.compile(r"^(?P<type>[a-zA-Z0-9]+(\-[a-zA-Z0-9]+)*)$")
MEMLIMIT_MATCH = re.compile(r"^(?P<mem>(([0-9]+(MB|KB|GB|[BKMG])|0)(/([0-9]+(MB|KB|GB|[BKMG])))?))$", re.IGNORECASE)
CPUSHARE_MATCH = re.compile(r"^(?P<cpu>(([-+]?[0-9]*\.?[0-9]+[m]?)(/([-+]?[0-9]*\.?[0-9]+[m]?))?))$")
TAGVAL_MATCH = re.compile(r"^(?:[a-zA-Z\d][-\.\w]{0,61})?[a-zA-Z\d]$")
CONFIGKEY_MATCH = re.compile(r"^[a-z_]+[a-z0-9_]*$", re.IGNORECASE)


####################
# Resource Metrics #
####################
# TODO: 移到 apiserver 对应的模块
class SeriesMetricsResultSerializer(serializers.Serializer):
    type_name = serializers.CharField()
    results = serializers.ListField()
    display_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["display_name"] = MetricsSeriesType.get_choice_label(instance.type_name)
        return result


class ResourceMetricsResultSerializer(serializers.Serializer):
    type_name = serializers.CharField()
    results = SeriesMetricsResultSerializer(allow_null=True, many=True)


class InstanceMetricsResultSerializer(serializers.Serializer):
    instance_name = serializers.CharField()
    results = ResourceMetricsResultSerializer(allow_null=True, many=True)
    display_name = serializers.CharField(required=False)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["display_name"] = Instance.get_shorter_instance_name(instance.instance_name)
        return result
