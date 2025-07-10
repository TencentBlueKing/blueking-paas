# -*- coding: utf-8 -*-
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

import json
import logging
from collections import defaultdict
from functools import reduce
from operator import add
from typing import Counter, Dict, List, Optional

from elasticsearch_dsl.aggs import Terms
from rest_framework.fields import get_attribute

from paasng.accessories.log.models import ElasticSearchParams
from paasng.accessories.log.utils import get_es_term
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module
from paasng.utils import safe_jinja2
from paasng.utils.es_log.models import FieldFilter
from paasng.utils.es_log.search import SmartSearch
from paasng.utils.text import calculate_percentage

logger = logging.getLogger(__name__)


def agg_builtin_filters(search: SmartSearch, mappings: dict):
    """添加内置过滤条件查询语句, 内置过滤条件有 environment, process_id, stream"""
    for field_name in ["environment", "process_id", "stream"]:
        search = search.agg(
            field_name,
            Terms(
                field=get_es_term(field_name, mappings),
                # 不能设置太低, 否则应用的进程太多就会筛选不到
                size=10,
            ),
        )
    return search


def parse_properties_filters(mappings: dict) -> Dict[str, FieldFilter]:
    """从 mappings 中解析出 field filter"""
    # 为了简化 _clean_property 的递归代码, 传递给 _clean_property 时需要加上 {"properties": mappings} 这层封装
    all_properties_filters = {f.name: f for f in _clean_property([], {"properties": mappings})}
    # 从命名内置过滤条件, 内置过滤条件有 environment, process_id, stream
    for field_name in ["environment", "process_id", "stream"]:
        es_term = get_es_term(field_name, mappings)
        if field := all_properties_filters.get(es_term):
            field.name = field_name
    return all_properties_filters


def _clean_property(nested_name: List[str], mapping: Dict) -> List[FieldFilter]:
    """transform ES mapping to List[FieldFilter], will handle nested property by recursion

    Example Mapping:
    {
        "properties": {
            "age": {
                "type": "integer"
            },
            "email": {
                "type": "keyword"
            },
            "name": {
                "type": "text"
            },
            "nested": {
                "properties": {...}
            }
        }
    }
    """
    if "type" in mapping:
        field_name = ".".join(nested_name)
        return [FieldFilter(name=field_name, key=field_name if mapping["type"] != "text" else f"{field_name}.keyword")]
    if "properties" in mapping:
        nested_fields = [_clean_property(nested_name + [name], value) for name, value in mapping["properties"].items()]
        return reduce(add, nested_fields)
    return []


def count_filters_options_from_agg(aggregations: dict, properties: Dict[str, FieldFilter]) -> Dict[str, FieldFilter]:
    """根据 ES 聚合查询结果统计可用的过滤选项"""
    for field_name, agg in aggregations.items():
        if f := properties.get(field_name):
            f.options = [(bucket["key"], calculate_percentage(1, len(agg["buckets"]))) for bucket in agg["buckets"]]
    return properties


def count_filters_options_from_logs(logs: List, properties: Dict[str, FieldFilter]) -> Dict[str, FieldFilter]:
    """从日志样本(logs) 中统计 ES 日志的字段分布, 返回对应的 FieldFilters. 会忽略无可选 options 的 filters

    :param logs: 日志样本
    :param properties: 需要统计的ES 字段
    """
    # 在内存中统计 filters 的可选值
    field_counter: Dict[str, Counter] = defaultdict(Counter)
    log_fields = [(f, f.split(".")) for f in properties]
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

    result = {}
    for title, values in field_counter.items():
        f = properties[title]
        options = dict(f.options)
        total = sum(values.values())
        if total == 0 and len(options) == 0:
            # 该 field 无值可选时, 不允许使用该字段作为过滤条件
            continue

        for value, count in values.items():
            if value not in options:
                percentage = calculate_percentage(count, total)
                options[value] = percentage
        result[title] = FieldFilter(
            name=f.name,
            key=f.key,
            options=list(options.items()),
            total=total,
        )
    return result


class ESFilter:
    """ESFilter will modify the filtering conditions of the search based on the search_params.

    :param search_params: ElasticSearchParams
    """

    def __init__(self, search_params: ElasticSearchParams, mappings: Optional[Dict] = None):
        self.search_params = search_params
        self.mappings = mappings or {}

    def filter_by_builtin_filters(self, search: SmartSearch) -> SmartSearch:
        """根据 params 配置的 builtinFilters 添加过滤条件"""
        if not self.search_params.builtinFilters:
            return search
        for key, value in self.search_params.builtinFilters.items():
            if isinstance(value, str):
                search = search.filter("term", **{get_es_term(key, self.mappings): value})
            else:
                search = search.filter("terms", **{get_es_term(key, self.mappings): value})
        return search

    def filter_by_builtin_excludes(self, search: SmartSearch) -> SmartSearch:
        """根据 params 配置的 builtinExcludes 添加过滤条件"""
        if not self.search_params.builtinExcludes:
            return search
        for key, value in self.search_params.builtinExcludes.items():
            if isinstance(value, str):
                search = search.exclude("term", **{get_es_term(key, self.mappings): value})
            else:
                search = search.exclude("terms", **{get_es_term(key, self.mappings): value})
        return search


tmpl_converters = {
    "@json": lambda v: json.loads(v),
    "@jinja": lambda v, context: safe_jinja2.Template(v).render(**context),
}


class EnvFilter(ESFilter):
    """EnvFilter will modify the filtering conditions of the search based on the search_params and env context

    :param env: ModuleEnvironment context to filter
    :param search_params: ElasticSearchParams
    """

    def __init__(self, env: ModuleEnvironment, search_params: ElasticSearchParams, mappings: Optional[Dict] = None):
        super().__init__(search_params=search_params, mappings=mappings)
        self.env = env
        self.module = env.module
        self.application = env.application

    def filter_by_env(self, search: SmartSearch) -> SmartSearch:
        """为搜索增加环境相关过滤条件"""
        context = {
            "app_code": self.application.code,
            "module_name": self.module.name,
            "engine_app_name": self.env.get_engine_app().name.replace("_", "0us0"),
            "engine_app_names": [self.env.get_engine_app().name.replace("_", "0us0")],
        }
        term_fields = self.search_params.termTemplate.copy()
        for k, v in term_fields.items():
            term_fields[k] = safe_jinja2.Template(v).render(**context)

        # 目前只有查询 Ingress 日志时需要用 terms 过滤多字段
        # 接入日志平台后查询日志的交互需要调整, 不能再在模块维度查询日志
        # 待前端重构后即可删除这些兼容性代码, 暂不考虑在 search_params 中添加 terms 相关的模板渲染字段
        if "engine_app_name" in term_fields and "tojson" in self.search_params.termTemplate["engine_app_name"]:
            search = search.filter(
                "terms",
                **{get_es_term("engine_app_name", self.mappings): json.loads(term_fields.pop("engine_app_name"))},
            )
        if term_fields:
            # [term] query doesn't support multiple fields
            for k, v in term_fields.items():
                search = search.filter("term", **{get_es_term(k, self.mappings): v})
        return search


class ModuleFilter(ESFilter):
    """ModuleFilter will modify the filtering conditions of the search based on the search_params and module context

    [Deprecated]
    :param module: Module context to filter
    :param search_params: ElasticSearchParams
    """

    def __init__(self, module: Module, search_params: ElasticSearchParams, mappings: Optional[Dict] = None):
        super().__init__(search_params=search_params, mappings=mappings)
        self.module = module
        self.application = module.application

    def filter_by_module(self, search: SmartSearch) -> SmartSearch:
        """为搜索增加模块相关过滤条件"""
        context = {
            "app_code": self.application.code,
            "module_name": self.module.name,
            "engine_app_names": [env.get_engine_app().name.replace("_", "0us0") for env in self.module.get_envs()],
        }
        term_fields = self.search_params.termTemplate.copy()
        for k, v in term_fields.items():
            term_fields[k] = safe_jinja2.Template(v).render(**context)

        # 目前只有查询 Ingress 日志时需要用 terms 过滤多字段
        # 接入日志平台后查询日志的交互需要调整, 不能再在模块维度查询日志
        # 待前端重构后即可删除这些兼容性代码, 暂不考虑在 search_params 中添加 terms 相关的模板渲染字段
        if "engine_app_name" in term_fields:
            if "tojson" not in self.search_params.termTemplate["engine_app_name"]:
                raise ValueError("engine_app_name template must be using will tojson filter")
            search = search.filter(
                "terms",
                **{get_es_term("engine_app_name", self.mappings): json.loads(term_fields.pop("engine_app_name"))},
            )
        if term_fields:
            # [term] query doesn't support multiple fields
            for k, v in term_fields.items():
                search = search.filter("term", **{get_es_term(k, self.mappings): v})
        return search
