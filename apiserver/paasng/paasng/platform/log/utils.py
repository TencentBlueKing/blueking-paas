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
import datetime
import logging
import operator
import re
from functools import reduce
from itertools import chain
from operator import and_
from typing import TYPE_CHECKING, List

import pytz
from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch_dsl.query import Q, Query

if TYPE_CHECKING:
    from .models import SimpleDomainSpecialLanguage

logger = logging.getLogger(__name__)


def detect_indexes(start_time: datetime.datetime, end_time: datetime.datetime, index_pattern: str) -> List[str]:
    """
    get es indexes by time_range[start_time, end_time],
    which could speed up search process via only on specific indexes
    """
    client = Elasticsearch(settings.ELASTICSEARCH_HOSTS)
    key_pattern = "(?P<date>.+)"
    if key_pattern not in index_pattern:
        raise ValueError(f'Key pattern: "{key_pattern}" not found in index pattern: "{index_pattern}"')

    es_index_pattern = index_pattern.replace(key_pattern, "*")
    path = f"/{es_index_pattern}/_stats/fielddata?level=indices"
    params = {"request_timeout": settings.DEFAULT_ES_SEARCH_TIMEOUT}
    result = client.indices.transport.perform_request('GET', path, params=params)

    if not result:
        logger.error("_stats fail! [path=%s, params=%s, result=%s]", path, params, result)

    indexes = []
    pattern = re.compile(index_pattern)
    # there is no similar api in es7.x to filter index by timestamp
    # so we filter the index manually
    # maybe we should find out a more elegant way to filter index
    for x in result["indices"]:
        match_result = re.match(pattern, x)
        if not match_result:
            continue

        try:
            date_str = match_result.groupdict()["date"]
        except KeyError:
            logger.warning("index<%s> has error pattern", x)
            continue

        try:
            index_date = datetime.datetime.strptime(date_str, "%Y.%m.%d")
        except ValueError:
            if "grokfailure" not in date_str:
                logger.warning("index<%s> could not be parsed", x)
            continue

        if start_time.astimezone(pytz.UTC).date() <= index_date.date() <= end_time.astimezone(pytz.UTC).date():
            indexes.append(x)

    return indexes


def parse_simple_dsl_to_dsl(dsl: 'SimpleDomainSpecialLanguage', mappings: dict) -> Query:
    # use `MatchAll` as fallback
    query_string = (
        Q("query_string", query=dsl.query.query_string, analyze_wildcard=True) if bool(dsl.query.query_string) else Q()
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
