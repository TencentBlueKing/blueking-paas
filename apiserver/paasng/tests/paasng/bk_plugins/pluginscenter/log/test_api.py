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
from typing import Dict
from unittest import mock

import cattr
import pytest
from elasticsearch_dsl.aggs import DateHistogram
from elasticsearch_dsl.response import Hit
from elasticsearch_dsl.response.aggs import FieldBucketData
from elasticsearch_dsl.search import Search

from paasng.bk_plugins.pluginscenter.log import (
    aggregate_date_histogram,
    query_ingress_logs,
    query_standard_output_logs,
    query_structure_logs,
)
from paasng.bk_plugins.pluginscenter.log.client import LogClientProtocol
from paasng.utils.es_log.time_range import SmartTimeRange

pytestmark = pytest.mark.django_db


@pytest.fixture()
def log_client():
    with mock.patch(
        "paasng.bk_plugins.pluginscenter.log.instantiate_log_client", spec=LogClientProtocol, new=mock.MagicMock()
    ) as mock_client_factory:
        yield mock_client_factory()


@pytest.fixture()
def time_range():
    return SmartTimeRange(time_range="1h")


def make_hit(fields: Dict) -> Hit:
    return Hit({"fields": fields})


def test_query_standard_output_logs(pd, plugin, log_client, time_range):
    log_client.execute_search.return_value = (
        [
            make_hit({"@timestamp": 1, "json": {"message": "foo"}, "other": "FOO"}),
            make_hit({"@timestamp": 2, "json": {"message": "bar"}, "other": "BAR"}),
        ],
        20,
    )

    logs = query_standard_output_logs(pd, plugin, "nobody", time_range, "", 100, 0)
    assert cattr.unstructure(logs.logs) == [
        {"timestamp": 1, "message": "foo", "raw": {"@timestamp": 1, "json.message": "foo", "other": "FOO"}},
        {"timestamp": 2, "message": "bar", "raw": {"@timestamp": 2, "json.message": "bar", "other": "BAR"}},
    ]
    assert logs.total == 20
    assert json.loads(logs.dsl) == {
        "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h", "lte": "now"}}}]}},
        "sort": [{"@timestamp": {"order": "desc"}}],
        "size": 100,
        "from": 0,
    }


def test_query_structure_logs(pd, plugin, log_client, time_range):
    log_client.execute_search.return_value = (
        [
            make_hit({"@timestamp": 1, "json": {"message": "foo"}, "other": "FOO"}),
            make_hit({"@timestamp": 2, "json": {"message": "bar"}, "other": "BAR"}),
        ],
        20,
    )

    logs = query_structure_logs(pd, plugin, "nobody", time_range, "", 100, 0)
    assert cattr.unstructure(logs.logs) == [
        {"timestamp": 1, "message": "foo", "raw": {"@timestamp": 1, "json.message": "foo", "other": "FOO"}},
        {"timestamp": 2, "message": "bar", "raw": {"@timestamp": 2, "json.message": "bar", "other": "BAR"}},
    ]
    assert logs.total == 20
    assert json.loads(logs.dsl) == {
        "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h", "lte": "now"}}}]}},
        "sort": [{"@timestamp": {"order": "desc"}}],
        "size": 100,
        "from": 0,
    }


def test_query_ingress_logs(pd, plugin, log_client, time_range):
    log_client.execute_search.return_value = (
        [
            make_hit(
                {
                    "@timestamp": 1,
                    "json": {"message": "foo"},
                    "method": "GET",
                    "path": "/example",
                    "status_code": 200,
                    "response_time": 1.12,
                    "client_ip": "localhost",
                    "bytes_sent": 77777,
                    "user_agent": "foo client",
                    "http_version": "1.1",
                }
            ),
            make_hit(
                {
                    "@timestamp": 1,
                    "json": {"message": "foo"},
                    "method": "GET",
                    "path": "/example",
                    "status_code": "200",
                    "response_time": "1.12",
                    "client_ip": "localhost",
                    "bytes_sent": "77777",
                    "user_agent": "foo client",
                    "http_version": "1.1",
                }
            ),
        ],
        20,
    )

    logs = query_ingress_logs(pd, plugin, "nobody", time_range, "", 100, 0)
    assert cattr.unstructure(logs.logs) == [
        {
            "timestamp": 1,
            "message": "foo",
            "raw": {
                "@timestamp": 1,
                "json.message": "foo",
                "method": "GET",
                "path": "/example",
                "status_code": 200,
                "response_time": 1.12,
                "client_ip": "localhost",
                "bytes_sent": 77777,
                "user_agent": "foo client",
                "http_version": "1.1",
            },
            "method": "GET",
            "path": "/example",
            "status_code": 200,
            "response_time": 1.12,
            "client_ip": "localhost",
            "bytes_sent": 77777,
            "user_agent": "foo client",
            "http_version": "1.1",
        },
        {
            "timestamp": 1,
            "message": "foo",
            "raw": {
                "@timestamp": 1,
                "json.message": "foo",
                "method": "GET",
                "path": "/example",
                "status_code": "200",
                "response_time": "1.12",
                "client_ip": "localhost",
                "bytes_sent": "77777",
                "user_agent": "foo client",
                "http_version": "1.1",
            },
            "method": "GET",
            "path": "/example",
            "status_code": 200,
            "response_time": 1.12,
            "client_ip": "localhost",
            "bytes_sent": 77777,
            "user_agent": "foo client",
            "http_version": "1.1",
        },
    ]


def test_aggregate_date_histogram(pd, plugin, log_client, time_range):
    log_client.aggregate_date_histogram.return_value = FieldBucketData(
        DateHistogram(),
        Search(),
        {
            "buckets": [
                {"key": 1000, "doc_count": 12345},
                {"key": 2000, "doc_count": 54321},
                {"key": 1668064461002071000, "doc_count": 1},
            ]
        },
    )

    logs = aggregate_date_histogram(pd, plugin, "ingress", "nobody", time_range, "")
    assert logs.series == [12345, 54321, 1]
    assert logs.timestamps == [1, 2, 1668064461002071]
