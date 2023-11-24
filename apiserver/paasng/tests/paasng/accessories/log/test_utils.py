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

from paasng.accessories.log.dsl import SearchRequestSchema
from paasng.accessories.log.utils import NOT_SET, get_es_term, parse_request_to_es_dsl, rename_log_fields
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
    "query_term, mappings, expected",
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
        # 保留字测试
        ("pod_name", {}, "pod_name"),
        ("pod_name", {"__ext": {"properties": {"io_kubernetes_pod": {"type": "keyword"}}}}, "__ext.io_kubernetes_pod"),
        (
            "region",
            {
                "__ext": {
                    "properties": {"labels": {"properties": {"bkapp_paas_bk_tencent_com_region": {"type": "keyword"}}}}
                }
            },
            "__ext.labels.bkapp_paas_bk_tencent_com_region",
        ),
        (
            "app_code",
            {
                "__ext": {
                    "properties": {"labels": {"properties": {"bkapp_paas_bk_tencent_com_code": {"type": "keyword"}}}}
                }
            },
            "__ext.labels.bkapp_paas_bk_tencent_com_code",
        ),
        (
            "app_code",
            {
                "__ext": {
                    "properties": {"labels": {"properties": {"bkapp_paas_bk_tencent_com_code": {"type": "keyword"}}}}
                }
            },
            "__ext.labels.bkapp_paas_bk_tencent_com_code",
        ),
        (
            "module_name",
            {
                "__ext": {
                    "properties": {
                        "labels": {"properties": {"bkapp_paas_bk_tencent_com_module_name": {"type": "keyword"}}}
                    }
                }
            },
            "__ext.labels.bkapp_paas_bk_tencent_com_module_name",
        ),
        (
            "environment",
            {
                "__ext": {
                    "properties": {
                        "labels": {"properties": {"bkapp_paas_bk_tencent_com_environment": {"type": "keyword"}}}
                    }
                }
            },
            "__ext.labels.bkapp_paas_bk_tencent_com_environment",
        ),
        (
            "environment",
            {
                "__ext": {
                    "properties": {
                        "labels": {"properties": {"bkapp_paas_bk_tencent_com_environment": {"type": "keyword"}}}
                    }
                }
            },
            "__ext.labels.bkapp_paas_bk_tencent_com_environment",
        ),
        (
            "process_id",
            {
                "__ext": {
                    "properties": {
                        "labels": {"properties": {"bkapp_paas_bk_tencent_com_process_name": {"type": "keyword"}}}
                    }
                }
            },
            "__ext.labels.bkapp_paas_bk_tencent_com_process_name",
        ),
        (
            "environment",
            {
                "__ext": {
                    "properties": {
                        "labels": {"properties": {"bkapp_paas_bk_tencent_com_environment": {"type": "keyword"}}}
                    }
                }
            },
            "__ext.labels.bkapp_paas_bk_tencent_com_environment",
        ),
    ],
)
def test_get_es_term(query_term, mappings, expected):
    assert get_es_term(query_term, mappings) == expected


_default_log: dict = {
    "region": NOT_SET,
    "app_code": NOT_SET,
    "module_name": NOT_SET,
    "environment": NOT_SET,
    "process_id": NOT_SET,
    "pod_name": NOT_SET,
    "stream": NOT_SET,
}


@pytest.mark.parametrize(
    "log, expected",
    [
        (
            {"__ext.labels.bkapp_paas_bk_tencent_com_region": "default"},
            {**_default_log, "__ext.labels.bkapp_paas_bk_tencent_com_region": "default", "region": "default"},
        ),
        (
            {"__ext.labels.bkapp_paas_bk_tencent_com_environment": "stag"},
            {**_default_log, "__ext.labels.bkapp_paas_bk_tencent_com_environment": "stag", "environment": "stag"},
        ),
        (
            {
                "__ext.labels.bkapp_paas_bk_tencent_com_region": "default",
                "__ext.labels.bkapp_paas_bk_tencent_com_code": "code",
                "__ext.labels.bkapp_paas_bk_tencent_com_module_name": "default",
                "__ext.labels.bkapp_paas_bk_tencent_com_environment": "stag",
                "__ext.labels.bkapp_paas_bk_tencent_com_process_name": "web",
                "__ext.io_kubernetes_pod": "bkapp-code-stag--web-8449579sh9d2",
            },
            {
                "__ext.labels.bkapp_paas_bk_tencent_com_region": "default",
                "__ext.labels.bkapp_paas_bk_tencent_com_code": "code",
                "__ext.labels.bkapp_paas_bk_tencent_com_module_name": "default",
                "__ext.labels.bkapp_paas_bk_tencent_com_environment": "stag",
                "__ext.labels.bkapp_paas_bk_tencent_com_process_name": "web",
                "__ext.io_kubernetes_pod": "bkapp-code-stag--web-8449579sh9d2",
                "region": "default",
                "app_code": "code",
                "module_name": "default",
                "environment": "stag",
                "process_id": "web",
                "pod_name": "bkapp-code-stag--web-8449579sh9d2",
                "stream": NOT_SET,
            },
        ),
    ],
)
def test_rename_log_fields(log, expected):
    assert rename_log_fields(log) == expected


@pytest.mark.parametrize(
    "query_conditions, mappings, expected",
    [
        (
            SearchRequestSchema(query={"query_string": "foo"}),
            {},
            {"query_string": {"query": "foo", "analyze_wildcard": True}},
        ),
        (
            SearchRequestSchema(query={"query_string": "foo", "terms": {"app_code": {"foo"}}}),
            {},
            {
                "bool": {
                    "must": [
                        {"query_string": {"query": "foo", "analyze_wildcard": True}},
                        {"terms": {"app_code": ["foo"]}},
                    ]
                }
            },
        ),
        (
            SearchRequestSchema(query={"query_string": "foo", "terms": {"app_code": ["foo"]}}),
            {"app_code": {"type": "text"}},
            {
                "bool": {
                    "must": [
                        {"query_string": {"query": "foo", "analyze_wildcard": True}},
                        {"terms": {"app_code.keyword": ["foo"]}},
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
                "bool": {
                    "must": [
                        {"query_string": {"query": "foo", "analyze_wildcard": True}},
                        {"terms": {"app_code.keyword": ["foo"]}},
                    ],
                    "must_not": [{"terms": {"module_name": ["bar"]}}],
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
