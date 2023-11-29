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


class PaginationQuerySLZ(serializers.Serializer):
    offset = serializers.IntegerField(help_text="分页偏移", default=0, required=False)
    limit = serializers.IntegerField(help_text="分页大小", default=100, required=False)


class PaginationSLZ(serializers.Serializer):
    count = serializers.IntegerField(help_text="总数量")


class EventGenreListQuerySLZ(PaginationQuerySLZ):
    ordering = serializers.CharField(help_text="排序方式", default="created", required=False)
    uuid = serializers.ListField(
        child=serializers.CharField(), source="filters.uuid", help_text="类型ID", required=False
    )
    name = serializers.ListField(
        child=serializers.CharField(), source="filters.name", help_text="类型名称", required=False
    )
    source = serializers.ListField(
        child=serializers.CharField(), source="filters.source", help_text="告警源", required=False
    )


class EventGenreSLZ(serializers.Serializer):
    uuid = serializers.CharField(help_text="类型ID")
    name = serializers.CharField(help_text="类型名称")
    source = serializers.CharField(help_text="告警源")


class EventGenreListSLZ(PaginationSLZ):
    results = EventGenreSLZ(many=True)


class EventRecordTimeRangeSLZ(serializers.Serializer):
    start_after = serializers.DateTimeField(source="filters.start_after", help_text="时间开始范围", required=False)
    start_before = serializers.DateTimeField(source="filters.start_before", help_text="时间结束范围", required=False)


class EventRecordAppSummaryQuerySLZ(EventRecordTimeRangeSLZ):
    pass


class EventRecordListQuerySLZ(PaginationQuerySLZ, EventRecordTimeRangeSLZ):
    module = serializers.ListField(
        child=serializers.CharField(), source="labels.module", help_text="模块", required=False
    )
    env = serializers.ListField(child=serializers.CharField(), source="labels.env", help_text="环境", required=False)
    uuid = serializers.ListField(
        child=serializers.CharField(), source="filters.uuid", help_text="告警ID", required=False
    )
    search = serializers.CharField(help_text="搜索关键字", required=False)
    is_active = serializers.BooleanField(source="filters.is_active", help_text="是否激活", required=False)
    genre = serializers.ListField(
        child=serializers.CharField(), source="genre.uuid", help_text="类型ID", required=False
    )
    ordering = serializers.CharField(help_text="排序方式", default="-start", required=False)


class EventRecordSLZ(serializers.Serializer):
    uuid = serializers.UUIDField(help_text="告警ID")
    message = serializers.CharField(help_text="内容")
    is_active = serializers.BooleanField(help_text="是否激活")
    start = serializers.DateTimeField(help_text="开始时间")
    genre = EventGenreSLZ()
    app = serializers.CharField(source="labels.app", help_text="应用")
    module = serializers.CharField(source="labels.module", help_text="模块")
    env = serializers.CharField(source="labels.env", help_text="环境")


class EventRecordListSLZ(PaginationSLZ):
    results = EventRecordSLZ(many=True)


class EventRecordStatusSLZ(serializers.Serializer):
    uuid = serializers.UUIDField(help_text="状态 ID")
    executor = serializers.CharField(help_text="执行步骤")
    status = serializers.CharField(help_text="执行状态")
    created = serializers.DateTimeField(help_text="执行时间")
    details = serializers.DictField(help_text="执行详情", allow_null=True)


class EventRecordDetailsSLZ(EventRecordSLZ):
    status = serializers.ListField(child=EventRecordStatusSLZ(), help_text="执行状态", allow_null=True, min_length=0)


class EventRecordMetricsQuerySLZ(serializers.Serializer):
    start = serializers.DateTimeField(help_text="开始时间")
    end = serializers.DateTimeField(help_text="开始时间")
    step = serializers.CharField(default="1m", help_text="查询步长")


class EventRecordMetricsSLZ(serializers.Serializer):
    metric = serializers.DictField(help_text="维度")
    values = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()), help_text="趋势向量：（时间戳，指标）"
    )


class EventRecordMetricsResultSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="名称")
    operator = serializers.CharField(help_text="操作符")
    threshold = serializers.CharField(help_text="阈值")
    results = serializers.ListField(child=EventRecordMetricsSLZ(), help_text="指标")


class AppSummarySLZ(serializers.Serializer):
    app_code = serializers.CharField(source="app.code", help_text="应用ID")
    app_name = serializers.CharField(source="app.name", help_text="应用名称")
    logo_url = serializers.CharField(source="app.get_logo_url", help_text="应用logo")
    count = serializers.IntegerField(source="summary.count", help_text="记录数")
    record_ids = serializers.ListField(child=serializers.CharField(), source="summary.record_ids", help_text="记录ID")


class AppSummaryResultSLZ(serializers.Serializer):
    results = AppSummarySLZ(many=True)
