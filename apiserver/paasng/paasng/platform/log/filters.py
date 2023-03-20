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
from typing import Counter, Dict, List, Tuple

import jinja2
from attrs import define, field
from rest_framework.fields import get_attribute

from paasng.platform.log.models import ElasticSearchParams
from paasng.platform.modules.models import Module
from paasng.utils.es_log.search import SmartSearch
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


class ElasticSearchFilter:
    def __init__(self, module: Module, search_params: ElasticSearchParams):
        self.application = module.application
        self.module = module
        self.search_params = search_params

    def filter_by_module(self, search: SmartSearch) -> SmartSearch:
        """为搜索增加插件相关过滤条件"""
        context = {
            "app_code": self.application.code,
            "module_name": self.module.name,
            "region": self.application.region,
            "engine_app_names": [env.get_engine_app().name.replace("_", "0us0") for env in self.module.get_envs()],
        }
        fields = self.search_params.termTemplate.copy()
        for k, v in fields.items():
            fields[k] = jinja2.Template(v).render(**context)
        return search.filter("term", **fields)

    def filter_by_builtin_filters(self, search: SmartSearch) -> SmartSearch:
        """根据 params 配置的 builtinFilters 添加过滤条件"""
        if not self.search_params.builtinFilters:
            return search
        for key, value in self.search_params.builtinFilters.items():
            if isinstance(value, str):
                search = search.filter("term", **{key: value})
            else:
                search = search.filter("terms", **{key: value})
        return search

    def filter_by_builtin_excludes(self, search: SmartSearch) -> SmartSearch:
        """根据 params 配置的 builtinExcludes 添加过滤条件"""
        if not self.search_params.builtinExcludes:
            return search
        for key, value in self.search_params.builtinExcludes.items():
            if isinstance(value, str):
                search = search.exclude("term", **{key: value})
            else:
                search = search.exclude("terms", **{key: value})
        return search
