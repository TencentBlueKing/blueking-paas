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
from typing import Dict, Optional, Union
from uuid import UUID

import arrow
from django.utils.translation import ugettext_lazy as _
from kubernetes.utils.quantity import parse_quantity
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from paas_wl.cnative.specs.procs import CNativeProcSpec
from paas_wl.platform.applications.models import Release
from paas_wl.workloads.autoscaling.constants import ScalingMetricName, ScalingMetricType
from paas_wl.workloads.autoscaling.models import AutoscalingConfig
from paas_wl.workloads.processes.constants import ProcessUpdateType
from paas_wl.workloads.processes.models import Instance, ProcessSpec


class HumanizeDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        return arrow.get(value).humanize(locale="zh")


class InstanceForDisplaySLZ(serializers.Serializer):
    """Common serializer for representing Instance object, removes some extra
    large and sensitive fields such as "envs" """

    name = serializers.CharField(read_only=True)
    process_type = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True, source="shorter_name")
    image = serializers.CharField(read_only=True)
    start_time = serializers.CharField(read_only=True)
    state = serializers.SerializerMethodField(read_only=True, help_text='实例状态')
    state_message = serializers.CharField(read_only=True)
    ready = serializers.BooleanField(read_only=True)
    version = serializers.CharField(read_only=True)

    def get_state(self, obj: Instance) -> str:
        """Sometimes the target pod may enter into 'Running' phase without being ready,
        which may confuses users, translate those states into "Starting"
        """
        if not obj.ready and obj.state == "Running":
            # Not using word "Pending" because it's already an Kubernetes Pod state
            return "Starting"
        return obj.state


class ProcessSpecSLZ(serializers.Serializer):
    """Serializer for representing process packages

    Need to convert the resource limit to a number:
    "resource_limit": {
        "cpu": "100m",
        "memory": "64Mi"
    }
    "resource_limit_quota": {
        "cpu": 100,
        "memory": 64
    }
    """

    name = serializers.CharField()
    target_replicas = serializers.IntegerField()
    target_status = serializers.CharField()
    max_replicas = serializers.IntegerField(source='plan.max_replicas')
    resource_limit = serializers.JSONField(source='plan.limits')
    resource_requests = serializers.JSONField(source='plan.requests')
    plan_id = serializers.CharField(source="plan.id")
    plan_name = serializers.CharField(source="plan.name")
    resource_limit_quota = serializers.SerializerMethodField(read_only=True)
    autoscaling = serializers.BooleanField()
    scaling_config = serializers.JSONField()

    def get_resource_limit_quota(self, obj: ProcessSpec) -> dict:
        limits = obj.plan.limits
        # 内存的单位为 Mi
        memory_quota = int(parse_quantity(limits['memory']) / (1024 * 1024))
        # CPU 的单位为 m
        cpu_quota = int(parse_quantity(limits['cpu']) * 1000)
        return {"cpu": cpu_quota, "memory": memory_quota}


class CNativeProcSpecSLZ(serializers.Serializer):
    """Format cloud-native process specs"""

    name = serializers.CharField()
    target_replicas = serializers.IntegerField()
    target_status = serializers.CharField()
    max_replicas = serializers.IntegerField()
    cpu_limit = serializers.CharField()
    memory_limit = serializers.CharField()
    resource_limit_quota = serializers.SerializerMethodField(read_only=True)

    def get_resource_limit_quota(self, obj: CNativeProcSpec) -> dict:
        # 内存的单位为 Mi
        memory_quota = int(parse_quantity(obj.memory_limit) / (1024 * 1024))
        # CPU 的单位为 m
        cpu_quota = int(parse_quantity(obj.cpu_limit) * 1000)
        return {"cpu": cpu_quota, "memory": memory_quota}


class ScaleMetricSLZ(serializers.Serializer):
    """扩缩容指标"""

    name = serializers.ChoiceField(required=True, choices=ScalingMetricName.get_choices())
    type = serializers.ChoiceField(required=True, choices=ScalingMetricType.get_choices())
    value = serializers.IntegerField(required=True, help_text=_('资源指标值/百分比'))
    raw_value = serializers.SerializerMethodField()

    def get_raw_value(self, attrs) -> Union[str, int]:
        """获取带单位的字面值"""
        if attrs['type'] == ScalingMetricType.AVERAGE_VALUE:
            value_tmpl = '{}m' if attrs['name'] == ScalingMetricName.CPU else '{}Mi'
            return value_tmpl.format(attrs['value'])

        return attrs['value']


class ScalingConfigSLZ(serializers.Serializer):
    """扩缩容配置"""

    min_replicas = serializers.IntegerField(required=True, min_value=1, help_text=_('最小副本数'))
    max_replicas = serializers.IntegerField(required=True, min_value=1, help_text=_('最大副本数'))
    metrics = serializers.ListField(child=ScaleMetricSLZ(), required=True, min_length=1, help_text=_('扩缩容指标'))


class UpdateProcessSLZ(serializers.Serializer):
    """Serializer for updating processes"""

    process_type = serializers.CharField(required=True)
    operate_type = serializers.ChoiceField(required=True, choices=ProcessUpdateType.get_django_choices())
    target_replicas = serializers.IntegerField(required=False, min_value=1, help_text=_('目标进程副本数'))
    autoscaling = serializers.BooleanField(required=False, default=False, help_text=_('是否开启自动扩缩容'))
    scaling_config = ScalingConfigSLZ(required=False, help_text=_('进程扩缩容配置'))

    def validate(self, attrs: Dict) -> Dict:
        if attrs['operate_type'] == ProcessUpdateType.SCALE:
            if attrs['autoscaling']:
                if not attrs.get('scaling_config'):
                    raise ValidationError(_('当启用自动扩缩容时，必须提供有效的 scaling_config'))
            elif not attrs.get('target_replicas'):
                raise ValidationError(_('当操作类型为扩缩容时，必须提供有效的 target_replicas'))

        return attrs

    def validate_scaling_config(self, config: Dict) -> Optional[AutoscalingConfig]:
        if not config:
            return None
        try:
            return AutoscalingConfig(**config)
        except Exception:
            raise ValidationError(_('scaling_config 配置格式有误'))


class ListProcessesSLZ(serializers.Serializer):
    """Serializer for listing processes"""

    release_id = serializers.UUIDField(default=None, help_text="用于过滤实例的发布ID")

    def validate_release_id(self, release_id: Optional[UUID]) -> Optional[UUID]:
        """Validate release_id by querying database"""
        if not release_id:
            return None

        try:
            self.context['wl_app'].release_set.get(pk=release_id)
        except Release.DoesNotExist:
            raise ValidationError(f'Release with id={release_id} do not exists')
        return release_id


class WatchProcessesSLZ(serializers.Serializer):
    """Serializer for watching processes"""

    timeout_seconds = serializers.IntegerField(required=False, default=30, max_value=120)
    rv_proc = serializers.CharField(required=True)
    rv_inst = serializers.CharField(required=True)
