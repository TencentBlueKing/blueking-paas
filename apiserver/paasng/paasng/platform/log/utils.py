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
from functools import reduce
from itertools import chain
from operator import and_
from typing import TYPE_CHECKING, Any, Dict, List

from elasticsearch_dsl.query import Q, Query
from elasticsearch_dsl.response import Hit

from paasng.platform.log.models import ElasticSearchParams
from paasng.utils.es_log.misc import flatten_structure, format_timestamp
from paasng.utils.es_log.models import NOT_SET, FlattenLog, field_extractor_factory

if TYPE_CHECKING:
    from .dsl import SearchRequestSchema

logger = logging.getLogger(__name__)


def parse_request_to_es_dsl(dsl: 'SearchRequestSchema', mappings: dict) -> Query:
    # use `MatchAll` as fallback
    query_string = (
        Q("query_string", query=dsl.query.query_string, analyze_wildcard=True) if dsl.query.query_string else Q()
    )
    # 空数组不进行过滤
    terms = [Q("terms", **{get_es_term(k, mappings): v}) for k, v in dsl.query.terms.items() if len(v) != 0]
    excludes = [~Q("terms", **{get_es_term(k, mappings): v}) for k, v in dsl.query.exclude.items() if len(v) != 0]
    return reduce(and_, [query_string, *terms, *excludes])


def get_es_term(query_term: str, mappings: dict) -> str:
    """根据 ES 中的字段类型，返回查询 term
    :param query_term: 前端查询关键字
    :param mappings: 从 ES 中获取的 properties mapping
    """
    try:
        target = mappings[query_term]
    except KeyError:
        parts = query_term.split(".")
        if len(parts) == 1:
            # ES mapping 中不存在该字段信息，直接返回
            return query_term

        # 去掉最后一个 "properties"
        # ["json", "levelname"] -> ["json", "properties", "levelname"]
        parts = list(chain.from_iterable(zip(parts, ["properties"] * len(parts))))[:-1]
        try:
            target = reduce(operator.getitem, parts, mappings)
        except KeyError:
            logger.warning("can't parse %s from mappings, return what it is", query_term)
            return query_term

    if target["type"] == "text":
        return f"{query_term}.keyword"
    else:
        return query_term


def rename_log_fields(raw_log: Dict[str, Any]):
    """调整 log 字段名称"""
    # [deprecated] 如果 region 不存在, 将 kubernetes.labels.region 重命名为 region
    # TODO: 去掉 region 字段
    raw_log["region"] = raw_log.get("region") or raw_log.get("kubernetes.labels.region") or NOT_SET

    # [deprecated] 如果 app_code 不存在, 将 kubernetes.labels.app_code 重命名为 app_code
    # TODO: 去掉 app_code 字段
    raw_log["app_code"] = raw_log.get("app_code") or raw_log.get("kubernetes.labels.app_code") or NOT_SET

    # [deprecated] 如果 module_name 不存在, 将 kubernetes.labels.module_name 重命名为 app_code
    # TODO: 去掉 module_name 字段
    raw_log["module_name"] = raw_log.get("module_name") or raw_log.get("kubernetes.labels.module_name") or NOT_SET

    # [deprecated] 如果 environment 不存在, 将 kubernetes.labels.env 重命名为 app_code
    # TODO: 去掉 environment 字段
    raw_log["environment"] = raw_log.get("environment") or raw_log.get("kubernetes.labels.env") or NOT_SET

    # 如果 process_id 不存在, 将 process_type 或 kubernetes.labels.process_id 重命名为 process_id
    raw_log["process_id"] = (
        raw_log.get("process_id")
        or raw_log.get("process_type")
        or raw_log.get("kubernetes.labels.process_id")
        or NOT_SET
    )

    # 如果 pod_name 不存在, 将 kubernetes.pod.name 重命名为 pod_name
    raw_log["pod_name"] = raw_log.get("pod_name") or raw_log.get("kubernetes.pod.name") or NOT_SET

    return raw_log


def clean_logs(
    logs: List[Hit],
    search_params: ElasticSearchParams,
) -> List[FlattenLog]:
    """从 ES 日志中转换成扁平化的 FlattenLog, 方便后续对日志字段的提取"""
    cleaned: List[FlattenLog] = []
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
                raw=raw,
            )
        )
    return cleaned
