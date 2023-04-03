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
import json
import logging
from collections import defaultdict
from operator import attrgetter
from typing import Counter, Dict, List

import jinja2
from rest_framework.fields import get_attribute

from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.log.models import ElasticSearchParams
from paasng.platform.modules.models import Module
from paasng.utils.es_log.models import FieldFilter
from paasng.utils.es_log.search import SmartSearch
from paasng.utils.text import calculate_percentage

logger = logging.getLogger(__name__)


def count_filters_options(logs: List, properties: Dict[str, FieldFilter]) -> List[FieldFilter]:
    """从日志样本(logs) 中统计 ES 日志的字段分布, 返回对应的 FieldFilters

    :param logs: 日志样本
    :param properties: 需要统计的ES 字段
    """
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


class ESFilter:
    """ESFilter will modify the filtering conditions of the search based on the search_params.

    :param search_params: ElasticSearchParams
    """

    def __init__(self, search_params: ElasticSearchParams):
        self.search_params = search_params

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


tmpl_converters = {"@json": lambda v: json.loads(v), "@jinja": lambda v, context: jinja2.Template(v).render(**context)}


class EnvFilter(ESFilter):
    """EnvFilter will modify the filtering conditions of the search based on the search_params and env context

    :param env: ModuleEnvironment context to filter
    :param search_params: ElasticSearchParams
    """

    def __init__(self, env: ModuleEnvironment, search_params: ElasticSearchParams):
        super().__init__(search_params=search_params)
        self.env = env
        self.module = env.module
        self.application = env.application

    def filter_by_env(self, search: SmartSearch) -> SmartSearch:
        """为搜索增加环境相关过滤条件"""
        context = {
            "app_code": self.application.code,
            "module_name": self.module.name,
            "region": self.application.region,
            "engine_app_name": self.env.get_engine_app().name.replace("_", "0us0"),
            "engine_app_names": [self.env.get_engine_app().name.replace("_", "0us0")],
        }
        term_fields = self.search_params.termTemplate.copy()
        for k, v in term_fields.items():
            term_fields[k] = jinja2.Template(v).render(**context)

        # 目前只有查询 Ingress 日志时需要用 terms 过滤多字段
        # 接入日志平台后查询日志的交互需要调整, 不能再在模块维度查询日志
        # 待前端重构后即可删除这些兼容性代码, 暂不考虑在 search_params 中添加 terms 相关的模板渲染字段
        if "engine_app_name" in term_fields and "tojson" in self.search_params.termTemplate["engine_app_name"]:
            search = search.filter("terms", engine_app_name=json.loads(term_fields.pop("engine_app_name")))
        if term_fields:
            # [term] query doesn't support multiple fields
            for k, v in term_fields.items():
                search = search.filter("term", **{k: v})
        return search


class ModuleFilter(ESFilter):
    """ModuleFilter will modify the filtering conditions of the search based on the search_params and module context

    [Deprecated]
    :param module: Module context to filter
    :param search_params: ElasticSearchParams
    """

    def __init__(self, module: Module, search_params: ElasticSearchParams):
        super().__init__(search_params=search_params)
        self.module = module
        self.application = module.application

    def filter_by_module(self, search: SmartSearch) -> SmartSearch:
        """为搜索增加模块相关过滤条件"""
        context = {
            "app_code": self.application.code,
            "module_name": self.module.name,
            "region": self.application.region,
            "engine_app_names": [env.get_engine_app().name.replace("_", "0us0") for env in self.module.get_envs()],
        }
        term_fields = self.search_params.termTemplate.copy()
        for k, v in term_fields.items():
            term_fields[k] = jinja2.Template(v).render(**context)

        # 目前只有查询 Ingress 日志时需要用 terms 过滤多字段
        # 接入日志平台后查询日志的交互需要调整, 不能再在模块维度查询日志
        # 待前端重构后即可删除这些兼容性代码, 暂不考虑在 search_params 中添加 terms 相关的模板渲染字段
        if "engine_app_name" in term_fields:
            if "tojson" not in self.search_params.termTemplate["engine_app_name"]:
                raise ValueError("engine_app_name template must be using will tojson filter")
            search = search.filter("terms", engine_app_name=json.loads(term_fields.pop("engine_app_name")))
        if term_fields:
            # [term] query doesn't support multiple fields
            for k, v in term_fields.items():
                search = search.filter("term", **{k: v})
        return search
