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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .constants import LogTimeType, LogType


class StandardOutputLogLineSLZ(serializers.Serializer):
    """标准输出日志(每行)"""

    timestamp = serializers.IntegerField(help_text="时间戳")
    message = serializers.CharField(help_text="日志内容")

    region = serializers.CharField()
    app_code = serializers.CharField()
    environment = serializers.CharField()
    process_id = serializers.CharField(allow_null=True, allow_blank=True)


class StandardOutputLogsSLZ(serializers.Serializer):
    """标准输出日志"""

    logs = StandardOutputLogLineSLZ(many=True)
    total = serializers.IntegerField(help_text="总日志量, 用于计算页数")
    dsl = serializers.CharField(help_text="日志查询语句")


class StructureLogLineSLZ(serializers.Serializer):
    """结构化日志(每行)"""

    timestamp = serializers.IntegerField(help_text="时间戳")
    message = serializers.CharField(help_text="日志内容")
    detail = serializers.DictField(help_text="日志详情")

    region = serializers.CharField()
    app_code = serializers.CharField()
    environment = serializers.CharField()
    process_id = serializers.CharField(allow_null=True, allow_blank=True)


class StructureLogsSLZ(serializers.Serializer):
    """结构化日志"""

    logs = StructureLogLineSLZ(many=True)
    total = serializers.IntegerField(help_text="总日志量, 用于计算页数")
    dsl = serializers.CharField(help_text="日志查询语句")


class IngressLogLineSLZ(serializers.Serializer):
    """Ingress 访问日志(每行)"""

    timestamp = serializers.IntegerField(help_text="时间戳")
    message = serializers.CharField(help_text="日志内容")
    method = serializers.CharField(help_text="请求方法", default=None)
    path = serializers.CharField(help_text="请求路径", default=None)
    status_code = serializers.IntegerField(help_text="状态码", default=None)
    response_time = serializers.FloatField(help_text="返回耗时", default=None)
    client_ip = serializers.CharField(help_text="客户端IP", default=None)
    bytes_sent = serializers.IntegerField(help_text="返回体大小", default=None)
    user_agent = serializers.CharField(help_text="UserAgent", default=None)
    http_version = serializers.CharField(help_text="http 版本号", default=None)


class IngressLogSLZ(serializers.Serializer):
    """Ingress 访问日志"""

    logs = IngressLogLineSLZ(many=True)
    total = serializers.IntegerField(help_text="总日志量, 用于计算页数")
    dsl = serializers.CharField(help_text="日志查询语句")


class DateHistogramSLZ(serializers.Serializer):
    """插件日志基于时间分布的直方图"""

    series = serializers.ListField(child=serializers.IntegerField(), help_text="按时间排序的值(文档数)")
    timestamps = serializers.ListField(child=serializers.IntegerField(), help_text="Series 中对应位置记录的时间点的时间戳")
    dsl = serializers.CharField(help_text="日志查询语句")


class LogFieldFilterSLZ(serializers.Serializer):
    """日志可选字段"""

    name = serializers.CharField(help_text="展示名称")
    key = serializers.CharField(help_text="传递给参数中的key")
    options = serializers.ListField(help_text="该字段的选项和分布频率")
    total = serializers.IntegerField(help_text="该字段在日志(top200)出现的频次")


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
