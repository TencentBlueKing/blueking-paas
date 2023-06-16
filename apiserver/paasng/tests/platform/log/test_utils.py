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
from typing import Dict, List

import pytest

from paasng.platform.log.dsl import SearchRequestSchema
from paasng.platform.log.utils import get_es_term, parse_request_to_es_dsl
from paasng.utils.datetime import convert_timestamp_to_str
from paasng.utils.es_log.misc import format_timestamp


@pytest.fixture
def make_stats_indexes_fake_resp():
    def _make_stats_indexes_fake_resp(indexes: List[str]):
        def _wrapper(*args, **kwargs):
            results: Dict[str, Dict] = {}
            for index in indexes:
                results[index] = {}

            return {"indices": results}

        return _wrapper

    return _make_stats_indexes_fake_resp


@pytest.mark.parametrize(
    "query_term,mappings,expected",
    [
        ("dd", {"dd": {"type": "text"}}, "dd.keyword"),
        ("dd", {"dd": {"type": "int"}}, "dd"),
        ("dd", {"dd": {"type": "keyword"}}, "dd"),
        ("dd", {"xxx": {"type": "keyword"}}, "dd"),
        ("json.levelname", {"json": {"properties": {"levelname": {"type": "text"}}}}, "json.levelname.keyword"),
        ("json.levelname", {"json": {"properties": {"levelname": {"type": "keyword"}}}}, "json.levelname"),
        (
            "json.levelname.no",
            {"json": {"properties": {"levelname": {"properties": {"no": {"type": "keyword"}}}}}},
            "json.levelname.no",
        ),
        (
            "json.levelname.no",
            {"json": {"properties": {"levelname": {"properties": {"no": {"type": "text"}}}}}},
            "json.levelname.no.keyword",
        ),
    ],
)
def test_get_es_term(query_term, mappings, expected):
    assert get_es_term(query_term, mappings) == expected


@pytest.mark.parametrize(
    "query_conditions, mappings, expected",
    [
        (
            SearchRequestSchema(query={"query_string": "foo"}),
            {},
            {'query_string': {'query': 'foo', 'analyze_wildcard': True}},
        ),
        (
            SearchRequestSchema(query={"query_string": "foo", "terms": {"app_code": {"foo"}}}),
            {},
            {
                'bool': {
                    'must': [
                        {'query_string': {'query': 'foo', 'analyze_wildcard': True}},
                        {'terms': {'app_code': ['foo']}},
                    ]
                }
            },
        ),
        (
            SearchRequestSchema(query={"query_string": "foo", "terms": {"app_code": ["foo"]}}),
            {"app_code": {"type": "text"}},
            {
                'bool': {
                    'must': [
                        {'query_string': {'query': 'foo', 'analyze_wildcard': True}},
                        {'terms': {'app_code.keyword': ['foo']}},
                    ]
                }
            },
        ),
        (
            SearchRequestSchema(
                query={
                    "query_string": "foo",
                    "terms": {"app_code": ["foo"]},
                    "exclude": {"module_name": ["bar"]},
                },
                sort={"response_time": "desc"},
            ),
            {"app_code": {"type": "text"}},
            {
                'bool': {
                    'must': [
                        {'query_string': {'query': 'foo', 'analyze_wildcard': True}},
                        {'terms': {'app_code.keyword': ['foo']}},
                    ],
                    'must_not': [{'terms': {'module_name': ['bar']}}],
                }
            },
        ),
    ],
)
def test_parse_request_to_es_dsl(query_conditions, mappings, expected):
    assert parse_request_to_es_dsl(query_conditions, mappings).to_dict() == expected


# 新的日志只返回 timestamp(时间戳)
# 测试将 timestamp(时间戳) 转换成旧的 ts 字段的格式是否符合预期
@pytest.mark.parametrize(
    # es_timestamp 即 @timestamp 字段, 实际上这个字段存的是 datetime
    "es_timestamp, expected_ts",
    [
        ("2023-04-11T11:13:58.102Z", "2023-04-11 19:13:58"),
        ("2023-04-11T11:13:57.958Z", "2023-04-11 19:13:57"),
    ],
)
def test_legacy_ts_field(es_timestamp: str, expected_ts):
    timestamp = format_timestamp(es_timestamp, input_format="datetime")
    assert convert_timestamp_to_str(timestamp) == expected_ts
