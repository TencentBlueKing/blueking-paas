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
import logging
from collections import defaultdict
from operator import attrgetter
from typing import Counter, Dict, Generator, List, Tuple

from attrs import define, field
from elasticsearch_dsl import Search
from rest_framework.fields import get_attribute

from paasng.platform.log.constants import ESField
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.modules.models import Module
from paasng.utils.text import calculate_percentage

logger = logging.getLogger(__name__)


@define
class FieldFilter:
    # 查询字段的title
    name: str
    # query_term: get参数中的key
    key: str
    # 该field的可选项
    options: List[Tuple[str, str]] = field(factory=list)
    # 该 field 出现的总次数
    total: int = 0


def count_filters_options(logs: List, properties: Dict[str, FieldFilter]) -> List[FieldFilter]:
    """统计 ES 日志的可选字段, 并填充到 filters 的 options"""
    # 在内存中统计 filters 的可选值
    field_counter: Dict[str, Counter] = defaultdict(Counter)
    log_fields = [(f, f.split(".")) for f in properties.keys()]
    for log in logs:
        for log_field, split_log_field in log_fields:
            try:
                value = get_attribute(log, split_log_field)
            except (AttributeError, KeyError):
                continue
            try:
                field_counter[log_field][value] += 1
            except TypeError:
                logger.warning("Field<%s> got an unhashable value: %s", log_field, value)

    result = []
    for title, values in field_counter.items():
        options = []
        total = sum(values.values())
        if total == 0:
            # 该 field 无值可选时, 不允许使用该字段作为过滤条件
            continue

        for value, count in values.items():
            percentage = calculate_percentage(count, total)
            options.append((value, percentage))
        result.append(FieldFilter(name=title, key=properties[title].key, options=options, total=total))
    # 根据 field 在所有日志记录中出现的次数进行降序排序, 再根据 key 的字母序排序(保证前缀接近的 key 靠近在一起, 例如 json.*)
    return sorted(result, key=attrgetter("total", "key"), reverse=True)


class BaseAppFilter:

    fields: List[dict] = []

    def __init__(self, region: str, app_code: str, module_name: str):
        self.region = region
        self.app_code = app_code
        self.module_name = module_name

    def filter_by_app(self, query: Search, mappings: dict) -> Search:
        """为搜索增加应用相关过滤"""
        for f in self.get_es_fields():
            if getattr(self, f"get_field_{f.query_term}_value", None):
                query_value = getattr(self, f"get_field_{f.query_term}_value")()
            else:
                query_value = getattr(self, f.query_term)

            query = query.filter("terms" if f.is_multiple else "term", **{f.get_es_term(mappings): query_value})

        return query

    def get_es_fields(self) -> Generator[ESField, None, None]:
        """根据 fields 信息组装 ESField 对象列表"""
        for f in self.fields:
            yield ESField.parse_obj(f)


class AppLogFilter(BaseAppFilter):
    """应用日志过滤器"""

    fields = [
        {
            "title": "AppCode",
            "chinese_name": "应用 Code",
            "query_term": "app_code",
        },
        {
            "title": "ModuleName",
            "chinese_name": "模块名",
            "query_term": "module_name",
        },
        {
            "title": "Region",
            "chinese_name": "版本",
            "query_term": "region",
        },
    ]


class AppAccessLogFilter(BaseAppFilter):
    """应用访问日志过滤器"""

    fields = [
        {
            "title": "EngineAppName",
            "chinese_name": "Engine应用名",
            "query_term": "engine_app_name",
            "is_multiple": True,
        },
    ]

    def get_field_engine_app_name_value(self) -> List[str]:
        # 默认请求预发布&生产环境的日志，不作环境过滤
        return [
            x.replace("_", "0us0")
            for x in ModuleInitializer(
                Module.objects.get(application__code=self.app_code, name=self.module_name)
            ).list_engine_app_names()
        ]
