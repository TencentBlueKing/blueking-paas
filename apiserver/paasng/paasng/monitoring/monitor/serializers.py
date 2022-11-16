# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from rest_framework import serializers

from .alert_rules.manager import AlertRuleManager
from .models import AppAlertRule


class ListAlertRulesSLZ(serializers.Serializer):
    alert_code = serializers.CharField(required=False)
    environment = serializers.ChoiceField(choices=('stag', 'prod'), required=False)
    keyword = serializers.CharField(required=False)


class AlertRuleSLZ(serializers.ModelSerializer):
    threshold_expr = serializers.CharField()
    receivers = serializers.ListField(child=serializers.CharField(), min_length=1)
    enabled = serializers.BooleanField()

    class Meta:
        model = AppAlertRule
        fields = ('id', 'alert_code', 'display_name', 'enabled', 'environment', 'threshold_expr', 'receivers')
        extra_kwargs = {
            'alert_code': {'read_only': True},
            'display_name': {'read_only': True},
            'environment': {'read_only': True},
        }

    def update(self, instance, validated_data):
        manager = AlertRuleManager(instance.application)
        instance = manager.update_rule(
            instance,
            update_fields={
                'threshold_expr': validated_data['threshold_expr'],
                'receivers': validated_data['receivers'],
                'enabled': validated_data['enabled'],
            },
        )
        return instance


class SupportedAlertSLZ(serializers.Serializer):
    alert_code = serializers.CharField()
    display_name = serializers.CharField()
