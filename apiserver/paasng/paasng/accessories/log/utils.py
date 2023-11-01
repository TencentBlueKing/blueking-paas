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
import operator
import re
from functools import reduce
from itertools import chain
from operator import and_
from typing import TYPE_CHECKING, Any, Dict, List

from elasticsearch_dsl.query import Q, Query
from elasticsearch_dsl.response import Hit

from paasng.accessories.log.models import ElasticSearchParams
from paasng.utils.es_log.misc import flatten_structure, format_timestamp
from paasng.utils.es_log.models import NOT_SET, FlattenLog, field_extractor_factory

if TYPE_CHECKING:
    from .dsl import SearchRequestSchema

logger = logging.getLogger(__name__)


# 平台保留的日志字段与不同日志采集方案的映射关系
# ELK 方案与 k8s 相关的字段收集到 kubernetes
# bklog 方案与 k8s 相关的字段收集到 __ext
# 由于 ELK 方案是所有应用共用一个 ES index, 存在 mappings 互相干扰的问题
# 因此需要将保留字段同名的字段优先级提高, 避免在 ELK 方案中无法正常过滤(ELK 方案在 logstash 中有清洗保留字段的逻辑)
RESERVED_FIELDS = {
    # TODO: 移除 region 字段
    # 理由: region 字段并未使用
    "region": [
        "region",
        "kubernetes.labels.region",
        "kubernetes.labels.bkapp_paas_bk_tencent_com_region",
        "__ext.labels.region",
        "__ext.labels.bkapp_paas_bk_tencent_com_region",
    ],
    "app_code": [
        "app_code",
        "kubernetes.labels.bkapp_paas_bk_tencent_com_code",
        "__ext.labels.bkapp_paas_bk_tencent_com_code",
    ],
    "module_name": [
        "module_name",
        "kubernetes.labels.bkapp_paas_bk_tencent_com_module_name",
        "__ext.labels.bkapp_paas_bk_tencent_com_module_name",
    ],
    "environment": [
        "environment",
        "kubernetes.labels.bkapp_paas_bk_tencent_com_environment",
        "__ext.labels.bkapp_paas_bk_tencent_com_environment",
    ],
    "process_id": [
        # 普通应用记录进程名的 label 是 process_id
        # 云原生应用新增的记录进程名的 label 是 bkapp.paas.bk.tencent.com/process-name
        "process_id",
        "kubernetes.labels.process_id",
        "kubernetes.labels.bkapp_paas_bk_tencent_com_process_name",
        "__ext.labels.process_id",
        "__ext.labels.bkapp_paas_bk_tencent_com_process_name",
        "process_type",
    ],
    "pod_name": ["kubernetes.pod.name", "__ext.io_kubernetes_pod", "pod_name"],
    # TODO: 移除 stream 字段
    # 理由: bklog 无法从文件路径清洗出 stream
    "stream": ["stream"],
}


def parse_request_to_es_dsl(dsl: 'SearchRequestSchema', mappings: dict) -> Query:
    # use `MatchAll` as fallback
    query_string = (
        Q("query_string", query=dsl.query.query_string, analyze_wildcard=True) if dsl.query.query_string else Q()
    )
    # 空数组不进行过滤
    # 当 _expand__to_dot=True 时, 会将 bklog 的保留字段 __ext 转成 .ext, 导致查询异常
    terms = [
        Q("terms", **{get_es_term(k, mappings): v}, _expand__to_dot=False)
        for k, v in dsl.query.terms.items()
        if len(v) != 0
    ]
    excludes = [
        ~Q("terms", **{get_es_term(k, mappings): v}, _expand__to_dot=False)
        for k, v in dsl.query.exclude.items()
        if len(v) != 0
    ]
    return reduce(and_, [query_string, *terms, *excludes])


def get_es_term(query_term: str, mappings: dict) -> str:
    """根据 ES 中的字段类型，返回查询 term

    :param query_term: 前端查询关键字
    :param mappings: 从 ES 中获取的 properties mapping
    """
    if query_term in RESERVED_FIELDS:
        for possible_field in RESERVED_FIELDS[query_term]:
            try:
                return try_get_es_term(possible_field, mappings)
            except KeyError:
                continue

    try:
        return try_get_es_term(query_term, mappings)
    except KeyError:
        return query_term


def try_get_es_term(query_term: str, mappings: dict) -> str:
    """根据 ES 中的字段类型，返回查询 term

    :param query_term: 前端查询关键字
    :param mappings: 从 ES 中获取的 properties mapping
    :raise KeyError: 当无法从 mappings 中解析出 term 时, 抛异常 KeyError
    """
    try:
        target = mappings[query_term]
    except KeyError:
        parts = query_term.split(".")
        if len(parts) == 1:
            # ES mapping 中不存在该字段信息，抛出 KeyError 异常
            raise KeyError(query_term)
        # 补充 "properties"
        # ["json", "levelname"] -> ["json", "properties", "levelname"]
        # [:-1] 的含义是去掉最后一个 "properties"
        parts = list(chain.from_iterable(zip(parts, ["properties"] * len(parts))))[:-1]
        try:
            target = reduce(operator.getitem, parts, mappings)
        except KeyError:
            logger.warning("can't parse %s from mappings, return what it is", query_term)
            raise KeyError(query_term)

    if target["type"] == "text":
        return f"{query_term}.keyword"
    else:
        return query_term


def rename_log_fields(raw_log: Dict[str, Any]):
    """将 RESERVED_FIELDS 中记录的字段映射到 log"""
    for field, possible_fields in RESERVED_FIELDS.items():
        value = NOT_SET
        for pfield in possible_fields:
            value = raw_log.get(pfield, value)
        raw_log[field] = value

    return raw_log


def build_filed_matcher(pattern: str):
    """构造字段过滤器"""
    re_matcher = re.compile(pattern)

    def match(field: str) -> bool:
        # 保留字段, 永远返回 True
        if field in RESERVED_FIELDS:
            return True
        return bool(re_matcher.fullmatch(field))

    return match


def clean_logs(
    logs: List[Hit],
    search_params: ElasticSearchParams,
) -> List[FlattenLog]:
    """从 ES 日志中转换成扁平化的 FlattenLog, 方便后续对日志字段的提取"""
    cleaned: List[FlattenLog] = []

    matcher = build_filed_matcher(search_params.filedMatcher) if search_params.filedMatcher is not None else None
    for log in logs:
        raw = flatten_structure(log.to_dict(), None)
        raw = rename_log_fields(raw)
        if hasattr(log.meta, "highlight") and log.meta.highlight:
            for k, v in log.meta.highlight.to_dict().items():
                raw[k] = "".join(v)

        cleaned.append(
            FlattenLog(
                timestamp=format_timestamp(
                    field_extractor_factory(search_params.timeField)(raw), search_params.timeFormat
                ),
                message=field_extractor_factory(search_params.messageField)(raw),
                # 如果设置了白名单, 则过滤白名单以外的字段(避免日志详情中太多字段)
                raw={k: v for k, v in raw.items() if matcher(k)} if matcher is not None else raw,
            )
        )
    return cleaned
