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
from pathlib import PurePosixPath
from typing import List

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_attribute

from paasng.accessories.log.constants import LogTimeChoices
from paasng.infras.bk_log.constatns import BkLogType
from paasng.utils.es_log.time_range import SmartTimeRange


class StandardOutputLogLineSLZ(serializers.Serializer):
    """标准输出日志(每行)"""

    timestamp = serializers.IntegerField(help_text="时间戳")
    message = serializers.CharField(help_text="日志内容")

    environment = serializers.CharField()
    process_id = serializers.CharField(allow_null=True, allow_blank=True)
    pod_name = serializers.CharField(required=True, help_text="Pod名称")


class StandardOutputLogsSLZ(serializers.Serializer):
    """标准输出日志"""

    logs = StandardOutputLogLineSLZ(many=True)
    total = serializers.IntegerField(help_text="总日志量, 用于计算页数")
    dsl = serializers.CharField(help_text="日志查询语句")
    scroll_id = serializers.CharField(required=True)


class StructureLogLineSLZ(serializers.Serializer):
    """结构化日志(每行)"""

    timestamp = serializers.IntegerField(help_text="时间戳")
    message = serializers.CharField(help_text="日志内容")
    detail = serializers.DictField(help_text="日志详情", source="raw")

    region = serializers.CharField()
    app_code = serializers.CharField()
    environment = serializers.CharField()
    process_id = serializers.CharField(allow_null=True, allow_blank=True)
    stream = serializers.CharField()


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


class LogQueryParamsSLZ(serializers.Serializer):
    """查询日志的 query 参数"""

    time_range = serializers.ChoiceField(choices=LogTimeChoices.get_choices(), required=True)
    start_time = serializers.DateTimeField(help_text="format %Y-%m-%d %H:%M:%S", allow_null=True, required=False)
    end_time = serializers.DateTimeField(help_text="format %Y-%m-%d %H:%M:%S", allow_null=True, required=False)
    offset = serializers.IntegerField(default=0, help_text="偏移量=页码*每页数量")
    limit = serializers.IntegerField(default=100, min_value=1, help_text="每页数量")
    scroll_id = serializers.CharField(required=False, help_text="仅标准输出日志需要该字段")

    # [deprecated] should use limit/offset instead
    page = serializers.IntegerField(min_value=1, required=False, help_text="页码")
    page_size = serializers.IntegerField(min_value=1, required=False, help_text="每页数量")

    def validate(self, attrs):
        try:
            time_range = SmartTimeRange(
                time_range=attrs["time_range"],
                start_time=attrs.get("start_time"),
                end_time=attrs.get("end_time"),
            )
        except ValueError as e:
            raise ValidationError({"time_range": str(e)})
        attrs["smart_time_range"] = time_range
        # deprecated, 兼容旧参数
        if "page_size" in attrs:
            attrs["limit"] = attrs["page_size"]
        if "page" in attrs:
            attrs["offset"] = (attrs["page"] - 1) * attrs["limit"]
        return attrs


class LogQueryDSLSLZ(serializers.Serializer):
    """查询日志的 DSL 参数"""

    query_string = serializers.CharField(help_text="查询语句", default="", allow_blank=True)
    terms = serializers.DictField(help_text="多值精准匹配", default=dict)
    exclude = serializers.DictField(help_text="terms 取反", default=dict)


class LogQueryBodySLZ(serializers.Serializer):
    """查询日志的 body 参数"""

    query = LogQueryDSLSLZ()


def get_is_builtin(self, data) -> bool:
    """判断自定义采集项是否平台内置的采集项"""
    return get_attribute(data, ["name_en"]) in self.context["builtin_config_names"]


class ModuleCustomCollectorConfigSLZ(serializers.Serializer):
    """自定义采集项配置(日志平台-自定义上报+日志采集规则)"""

    name_en = serializers.CharField(help_text="自定义采集项名称")
    collector_config_id = serializers.IntegerField(help_text="日志平台采集项ID")

    log_paths = serializers.ListField(child=serializers.CharField(help_text="日志文件的绝对路径，可使用 通配符"), default=list)
    log_type = serializers.ChoiceField(help_text="日志类型", choices=BkLogType.get_choices())
    is_builtin = serializers.SerializerMethodField(help_text="是否平台内置采集项")
    url = serializers.SerializerMethodField(help_text="日志平台链接")

    get_is_builtin = get_is_builtin

    def validate_log_paths(self, paths: List[str]):
        for path in paths:
            if not PurePosixPath(path).is_absolute():
                raise ValidationError(_("日志采集路径必须是绝对路径"))
        return paths

    def get_url(self, obj):
        return "{bk_log_url}/#/retrieve/{collector_config_id}?spaceUid={space_uid}".format(
            bk_log_url=settings.BK_LOG_URL,
            collector_config_id=obj.collector_config_id,
            space_uid=self.context["space_uid"],
        )


class BkLogCustomCollectorConfigSLZ(serializers.Serializer):
    """自定义采集项配置(日志平台-自定义上报-原始配置)"""

    name_en = serializers.CharField(help_text="自定义采集项名称")
    collector_config_id = serializers.IntegerField(help_text="日志平台采集项ID", source="id")
    is_builtin = serializers.SerializerMethodField(help_text="是否平台内置采集项")

    get_is_builtin = get_is_builtin


class BkLogCustomCollectMetadataQuerySLZ(serializers.Serializer):
    all = serializers.BooleanField(
        help_text="是否需要所有采集项",
        default=False,
    )


class BkLogCustomCollectMetadataOutputSLZ(serializers.Serializer):
    """日志采集配置额外数据"""

    options = BkLogCustomCollectorConfigSLZ(many=True, help_text="采集规则可选项")
    url = serializers.SerializerMethodField(help_text="日志平台创建自定义采集项规则")

    def get_url(self, value):
        return "{bk_log_url}/#/manage/custom-report/list?spaceUid={space_uid}".format(
            bk_log_url=settings.BK_LOG_URL,
            space_uid=self.context["space_uid"],
        )
