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
from typing import Dict, Optional
from uuid import UUID

import arrow
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from paas_wl.platform.applications.models import Release
from paas_wl.workloads.processes.constants import ProcessUpdateType
from paas_wl.workloads.processes.models import Instance


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
    """Serializer for representing process packages"""

    name = serializers.CharField()
    target_replicas = serializers.IntegerField()
    target_status = serializers.CharField()
    max_replicas = serializers.IntegerField(source='plan.max_replicas')
    resource_limit = serializers.JSONField(source='plan.limits')
    resource_requests = serializers.JSONField(source='plan.requests')
    plan_id = serializers.CharField(source="plan.id")
    plan_name = serializers.CharField(source="plan.name")


class CNativeProcSpecSLZ(serializers.Serializer):
    """Format cloud-native process specs"""

    name = serializers.CharField()
    target_replicas = serializers.IntegerField()
    target_status = serializers.CharField()
    max_replicas = serializers.IntegerField()


class UpdateProcessSLZ(serializers.Serializer):
    """Serializer for updating processes"""

    process_type = serializers.CharField(required=True)
    operate_type = serializers.ChoiceField(required=True, choices=ProcessUpdateType.get_django_choices())
    target_replicas = serializers.IntegerField(required=False, min_value=1, help_text='仅操作类型为 scale 时使用')

    def validate(self, data: Dict) -> Dict:
        if data['operate_type'] == ProcessUpdateType.SCALE and not data.get('target_replicas'):
            raise ValidationError(_('当操作类型为 scale 时，必须提供有效的 target_replicas'))
        return data


class ListProcessesSLZ(serializers.Serializer):
    """Serializer for listing processes"""

    release_id = serializers.UUIDField(default=None, help_text="用于过滤实例的发布ID")

    def validate_release_id(self, release_id: Optional[UUID]) -> Optional[UUID]:
        """Validate release_id by querying database"""
        if not release_id:
            return None

        try:
            self.context['engine_app'].release_set.get(pk=release_id)
        except Release.DoesNotExist:
            raise ValidationError(f'Release with id={release_id} do not exists')
        return release_id


class WatchProcessesSLZ(serializers.Serializer):
    """Serializer for watching processes"""

    timeout_seconds = serializers.IntegerField(required=False, default=30, max_value=120)
    rv_proc = serializers.CharField(required=True)
    rv_inst = serializers.CharField(required=True)
