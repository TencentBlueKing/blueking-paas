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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .constants import LogTimeType, LogType


class AppLogQuerySLZ(serializers.Serializer):
    time_range = serializers.ChoiceField(choices=LogTimeType.get_choices(), required=True)
    start_time = serializers.CharField(required=False)
    end_time = serializers.CharField(required=False)
    log_type = serializers.ChoiceField(required=False, default=LogType.STRUCTURED.value, choices=LogType.get_choices())

    def validate(self, attrs):
        if attrs['time_range'] != "customized":
            return attrs

        if not all(key in attrs for key in ['start_time', 'end_time']):
            raise serializers.ValidationError(_("自定义 time_range 时需要传入 start_time & end_time"))

        return attrs


class AppLogListQuerySLZ(AppLogQuerySLZ):
    # only for list
    page = serializers.IntegerField(min_value=1, required=True)
    page_size = serializers.IntegerField(min_value=1, required=True)


class AppIngressListQuerySLZ(AppLogQuerySLZ):
    # only for list
    page = serializers.IntegerField(min_value=1, required=True)
    page_size = serializers.IntegerField(min_value=1, required=True)
    log_type = serializers.ChoiceField(required=False, default=LogType.INGRESS.value, choices=LogType.get_choices())


class ESScrollSLZ(AppLogQuerySLZ):
    scroll_id = serializers.CharField(required=False, default=None)
