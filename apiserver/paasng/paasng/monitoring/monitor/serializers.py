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
from django.conf import settings
from rest_framework import serializers

from paasng.accessories.bkmonitorv3.params import QueryAlertsParams
from paasng.engine.constants import AppEnvName
from paasng.utils.serializers import HumanizeTimestampField

from .alert_rules.manager import AlertRuleManager
from .models import AppAlertRule


class ListAlertRulesSLZ(serializers.Serializer):
    alert_code = serializers.CharField(required=False)
    environment = serializers.ChoiceField(choices=AppEnvName.get_choices(), required=False)
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


class ListAlertsSLZ(serializers.Serializer):
    alert_code = serializers.CharField(required=False)
    environment = serializers.ChoiceField(choices=AppEnvName.get_choices(), required=False)
    # ABNORMAL: 表示未恢复, CLOSED: 已关闭, RECOVERED: 已恢复
    status = serializers.ChoiceField(choices=('ABNORMAL', 'CLOSED', 'RECOVERED'), required=False)
    keyword = serializers.CharField(required=False)
    start_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    end_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')

    def to_internal_value(self, data) -> QueryAlertsParams:
        data = super().to_internal_value(data)
        return QueryAlertsParams(app_code=self.context['app_code'], **data)

    def validate(self, data: QueryAlertsParams):
        if data.start_time > data.end_time:
            raise serializers.ValidationError("end_time must be greater than start_time")

        return data


class AlertSLZ(serializers.Serializer):
    id = serializers.CharField()
    alert_name = serializers.CharField()
    status = serializers.CharField()
    description = serializers.CharField()
    start_time = HumanizeTimestampField(help_text='告警开始时间', source='begin_time')
    end_time = HumanizeTimestampField(allow_null=True, help_text='告警结束时间')
    stage_display = serializers.CharField(help_text='处理阶段')
    receivers = serializers.ListField(
        child=serializers.CharField(), min_length=1, help_text='告警接收者', source='assignee'
    )
    detail_link = serializers.SerializerMethodField(help_text='详情链接')

    def get_detail_link(self, instance) -> str:
        bk_biz_id = settings.MONITOR_AS_CODE_CONF.get('bk_biz_id')
        return f"{settings.BK_MONITORV3_URL}/?bizId={bk_biz_id}/#/event-center/detail/{instance['id']}"
