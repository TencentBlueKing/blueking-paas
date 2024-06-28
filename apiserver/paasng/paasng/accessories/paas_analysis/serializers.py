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

from rest_framework.serializers import (
    BaseSerializer,
    BooleanField,
    CharField,
    ChoiceField,
    DateField,
    DateTimeField,
    DictField,
    IntegerField,
    ListSerializer,
    Serializer,
)

from paasng.accessories.paas_analysis.constants import MetricsDimensionType, MetricsInterval

#############
# Query SLZ #
#############


class IntervalMetricQuerySLZ(Serializer):
    interval = ChoiceField(help_text="时间片跨度, 5m: 5分钟; 1h: 1小时", choices=MetricsInterval.get_choices())
    start_time = DateTimeField()
    end_time = DateTimeField()
    fill_missing_data = BooleanField(
        help_text="当时间片的数据缺失时, 是否主动填充空数据(值为0的数据), 填充数据会影响性能", default=True
    )


class AggregatedMetricsQuerySLZ(Serializer):
    start_time = DateField()
    end_time = DateField()


class TableMetricsQuerySLZ(Serializer):
    interval = ChoiceField(
        help_text="时间片跨度, 5m: 5分钟; 1h: 1小时",
        choices=MetricsInterval.get_choices(),
        default=MetricsInterval.ONE_HOUR.value,
    )
    start_time = DateField()
    end_time = DateField()
    limit = IntegerField(default=30, help_text="数量限制, 用于分页")
    offset = IntegerField(default=0, help_text="偏移量, 用于分页")
    ordering = CharField(help_text="排序字段", allow_null=True, allow_blank=True, required=False)


############
# DATA SLZ #
############


def make_metric_table_slz(name: str, resource_slz: BaseSerializer):
    """通用表格的序列化器的生成器"""
    return type(name, (Serializer,), dict(meta=MetricTableMetaInfoSLZ(), resources=ListSerializer(child=resource_slz)))


def make_metric_wrapper_slz(name: str, data_slz: BaseSerializer, with_interval: bool = False):
    """通用 Metric 对象的序列化器的生成器"""
    attrs = dict(results=data_slz, source_type=CharField(), display_name=CharField())
    if with_interval:
        attrs["interval"] = ChoiceField(choices=MetricsInterval.get_choices(), allow_null=True)
    return type(name, (Serializer,), attrs)


class TimeRangeSLZ(Serializer):
    start_time = DateTimeField()
    end_time = DateTimeField()


class SiteSLZ(Serializer):
    """站点信息"""

    type = CharField()
    name = CharField()
    id = IntegerField()


class SupportedMetricsDimensionSLZ(Serializer):
    name = CharField()
    value = ChoiceField(choices=MetricsDimensionType.get_choices())


class PageViewMetricSLZ(Serializer):
    pv = IntegerField()
    uv = IntegerField()
    time = DateTimeField(allow_null=True, required=False)


class CustomEventMetricSLZ(Serializer):
    ev = IntegerField()
    ue = IntegerField()
    time = DateTimeField(allow_null=True, required=False)


class ResourceTypeSLZ(Serializer):
    name = ChoiceField(choices=MetricsDimensionType.get_choices())
    display_name = CharField()


class ColumnTypeSLZ(Serializer):
    name = CharField()
    display_name = CharField()
    sortable = BooleanField(default=False)


class MetricsDimensionSchemasSLZ(Serializer):
    resource_type = ResourceTypeSLZ()
    values_type = ListSerializer(child=ColumnTypeSLZ())


class PaginationSLZ(Serializer):
    total = IntegerField()


class MetricsDimensionMetaInfoSLZ(Serializer):
    schemas = MetricsDimensionSchemasSLZ()
    pagination = PaginationSLZ()


class MetricTableMetaInfoSLZ(Serializer):
    schemas = ListSerializer(child=ColumnTypeSLZ())
    pagination = PaginationSLZ()


class MetricsDimensionResourcesSLZ(Serializer):
    name = CharField(allow_blank=True)
    values = DictField()
    display_options = DictField(required=False, allow_null=True)


############
# 访问量统计 #
############


class MetricsDimensionSLZ(Serializer):
    """访问量统计按维度下钻的结果的序列化器"""

    meta = MetricsDimensionMetaInfoSLZ()
    resources = ListSerializer(child=MetricsDimensionResourcesSLZ())


class PageViewConfigSLZ(Serializer):
    site = SiteSLZ()
    time_range = TimeRangeSLZ()
    supported_dimension_type = ListSerializer(child=SupportedMetricsDimensionSLZ())
    metrics = make_metric_wrapper_slz("site-config-pv-metric", data_slz=PageViewMetricSLZ(), with_interval=False)()

    def validate_supported_dimension_type(self, data):
        # TODO: 待配置重构的时候, 这里需要实现过滤`用户`维度的功能
        return data


class PageViewTotalMetricSLZ(Serializer):
    site = SiteSLZ()
    result = make_metric_wrapper_slz('"site-total-pv-metric', data_slz=PageViewMetricSLZ(), with_interval=False)()


class PageViewMetricTrendSLZ(Serializer):
    site = SiteSLZ()
    result = make_metric_wrapper_slz("page-view-trend-metric", data_slz=ListSerializer(child=PageViewMetricSLZ()))()


############
# 自定义事件 #
############


class CustomEventConfigSLZ(Serializer):
    site = SiteSLZ()
    time_range = TimeRangeSLZ()
    metrics = make_metric_wrapper_slz("site-config-ce-metric", data_slz=CustomEventMetricSLZ(), with_interval=False)()


class CustomEventTotalMetricSLZ(Serializer):
    site = SiteSLZ()
    result = make_metric_wrapper_slz('"site-total-ce-metric', data_slz=CustomEventMetricSLZ(), with_interval=False)()


class CustomEventOverviewRecordSLZ(Serializer):
    """自定义事件概览单条记录的序列化器"""

    category = CharField()
    ev = IntegerField()
    ue = IntegerField()


class CustomEventDetailRecordSLZ(Serializer):
    """自定义事件某类别以某维度下钻的详情记录的序列化器"""

    event_id = CharField()
    action = CharField()
    ev = IntegerField()
    ue = IntegerField()


CustomEventOverviewTableSLZ = make_metric_table_slz("CustomEventOverviewTableSLZ", CustomEventOverviewRecordSLZ())

CustomEventDetailTableSLZ = make_metric_table_slz("CustomEventDetailTableSLZ", CustomEventDetailRecordSLZ())


class CustomEventMetricTrendSLZ(Serializer):
    """自定义事件指标变化趋势的序列化器"""

    site = SiteSLZ()
    result = make_metric_wrapper_slz(
        "custom-event-trend-metric", data_slz=ListSerializer(child=CustomEventMetricSLZ())
    )()


class IngressTrackingStatusSLZ(Serializer):
    """For managing ingress tracking status"""

    status = BooleanField(required=True, help_text="功能状态")
