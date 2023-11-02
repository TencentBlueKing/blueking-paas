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
from unittest import mock

import pytest
from elasticsearch_dsl.response import Hit, Response
from elasticsearch_dsl.search import Search

pytestmark = pytest.mark.django_db


class TestLegacyStdoutLogAPIView:
    def test_dsl(self, api_client, bk_app, bk_module):
        url = (
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/standard_output/list/?time_range=1h"
        )
        with mock.patch("paasng.accessories.log.views.logs.instantiate_log_client") as client_factory:
            client_factory().get_mappings.return_value = {"app_code": {"type": "text"}}
            # 无任何日志
            client_factory().execute_scroll_search.return_value = (
                Response(Search(), {"hits": {"hits": {}}, "_scroll_id": 1}),
                0,
            )
            response = api_client.post(
                url,
                data={
                    "query": {
                        "query_string": "query_string",
                        "terms": {"terms": ["foo", "bar"]},
                        "exclude": {"exclude": ["foo", "bar"]},
                    },
                    "sort": {"some-field": "asc"},
                },
            )

        assert response.data["data"]["total"] == 0
        assert response.data["data"]["logs"] == []
        # 测试 dsl 的拼接 是否符合预期
        assert json.loads(response.data["data"]["dsl"]) == {
            'query': {
                'bool': {
                    'filter': [
                        {'range': {'@timestamp': {'gte': 'now-1h', 'lte': 'now'}}},
                        # mappings 返回类型是 text, 因此添加了 .keyword
                        {'term': {'app_code.keyword': bk_app.code}},
                        {'term': {'module_name': bk_module.name}},
                        {'terms': {'stream': ['stderr', 'stdout']}},
                    ],
                    'must': [
                        {'query_string': {'query': 'query_string', 'analyze_wildcard': True}},
                        {'terms': {'terms': ['foo', 'bar']}},
                    ],
                    'must_not': [{'terms': {'exclude': ['foo', 'bar']}}],
                }
            },
            'sort': [{'@timestamp': {'order': 'desc'}, 'some-field': {'order': 'asc'}}],
            'size': 100,
            'from': 0,
            'highlight': {
                'fields': {'json.message': {'number_of_fragments': 0}},
                'pre_tags': ['[bk-mark]'],
                'post_tags': ['[/bk-mark]'],
                'require_field_match': False,
                'highlight_query': {
                    'bool': {
                        'must': [
                            {'query_string': {'query': 'query_string', 'analyze_wildcard': True}},
                            {'terms': {'terms': ['foo', 'bar']}},
                        ],
                        'must_not': [{'terms': {'exclude': ['foo', 'bar']}}],
                    }
                },
            },
        }

    def test_complex(self, api_client, bk_app, bk_module):
        url = (
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/standard_output/list/?time_range=1h"
        )
        with mock.patch("paasng.accessories.log.views.logs.instantiate_log_client") as client_factory:
            client_factory().execute_scroll_search.return_value = (
                Response(
                    Search(),
                    {
                        "hits": {
                            "hits": [
                                {
                                    "fields": {
                                        "@timestamp": 1,
                                        "json": {"message": "foo"},
                                        "one": {"two": {"three": "four"}},
                                        "region": bk_app.region,
                                        "app_code": bk_app.code,
                                        "module_name": bk_module.name,
                                        "environment": "stag",
                                        "process_id": "1234567",
                                        "stream": "foo",
                                        "pod_name": "bar",
                                    },
                                    "highlight": {"json.message": ["[bk-mark]", "???", "[/bk-mark]"]},
                                }
                            ]
                        },
                        "_scroll_id": "scroll_id",
                    },
                ),
                0,
            )
            response = api_client.post(
                url,
                data={
                    "query": {
                        "query_string": "query_string",
                        "terms": {"terms": ["foo", "bar"]},
                        "exclude": {"exclude": ["foo", "bar"]},
                    },
                    "sort": {"ts": "asc"},
                },
            )

        assert response.data["data"]["total"] == 0
        # 测试日志的解析是否符合预期
        assert response.data["data"]["scroll_id"] == "scroll_id"
        assert response.data["data"]["logs"] == [
            {
                'timestamp': '1970-01-01 08:00:01',
                # 高亮
                'message': '[bk-mark]???[/bk-mark]',
                # 没有 module_name
                'environment': 'stag',
                'process_id': '1234567',
                'pod_name': 'bar',
            }
        ]


class TestLegacySysStructuredLogAPIView:
    def test_complex(self, sys_api_client, bk_app, bk_module):
        url = (
            f"/sys/api/log/applications/{bk_app.code}/modules/{bk_module.name}/structured/list/?"
            f"time_range=1h&page=1&page_size=10"
        )
        with mock.patch("paasng.accessories.log.views.logs.instantiate_log_client") as client_factory:
            # 无任何日志
            client_factory().execute_search.return_value = (
                [
                    Hit(
                        {
                            "fields": {
                                "@timestamp": 1,
                                "json": {"message": "foo"},
                                "one": {"two": {"three": "four"}},
                                "region": bk_app.region,
                                "app_code": bk_app.code,
                                "module_name": bk_module.name,
                                "environment": "stag",
                                "process_id": "1234567",
                                "stream": "foo",
                                "pod_name": "bar",
                            },
                            "highlight": {"json.message": ["[bk-mark]", "???", "[/bk-mark]"]},
                        }
                    )
                ],
                0,
            )
            response = sys_api_client.post(
                url,
                data={
                    "query": {
                        "query_string": "query_string",
                        "terms": {"terms": ["foo", "bar"]},
                        "exclude": {"exclude": ["foo", "bar"]},
                    },
                    "sort": {"ts": "asc"},
                },
            )

        assert response.data["data"]["page"] == {"total": 0, "page": 1, "page_size": 10}
        # 测试日志的解析是否符合预期
        assert response.data["data"]["logs"] == [
            {
                'ts': '1970-01-01 08:00:01',
                # 高亮
                'message': '[bk-mark]???[/bk-mark]',
                'detail': {
                    # 不在白名单内的字段, 不返回
                    # "@timestamp": 1,
                    # "one.two.three": "four",
                    # 扁平化
                    'json.message': '[bk-mark]???[/bk-mark]',
                    'region': 'default',
                    'app_code': bk_app.code,
                    'module_name': bk_module.name,
                    'environment': 'stag',
                    'process_id': '1234567',
                    'stream': 'foo',
                    'pod_name': 'bar',
                },
                'region': bk_app.region,
                'app_code': bk_app.code,
                # 没有 module_name
                'environment': 'stag',
                'process_id': '1234567',
                'stream': 'foo',
            }
        ]


class TestSysBkPluginLogsViewset:
    def test_dsl(self, sys_api_client, bk_plugin_app):
        url = f"/sys/api/bk_plugins/{bk_plugin_app.code}/logs/?trace_id=foo&scroll_id=bar"
        with mock.patch("paasng.bk_plugins.bk_plugins.logging.instantiate_log_client") as client_factory:
            client_factory().get_mappings.return_value = {"app_code": {"type": "text"}}
            client_factory().execute_scroll_search.return_value = (
                Response(
                    Search(),
                    {
                        "hits": {"hits": []},
                        "_scroll_id": "scroll_id",
                    },
                ),
                0,
            )
            response = sys_api_client.get(url)
        assert response.data["logs"] == []
        # 测试 dsl 的拼接 是否符合预期
        assert json.loads(response.data["dsl"]) == {
            'query': {
                'bool': {
                    'filter': [
                        {'range': {'@timestamp': {'gte': 'now-14d', 'lte': 'now'}}},
                        # mappings 返回类型是 text, 因此添加了 .keyword
                        {'term': {'app_code.keyword': bk_plugin_app.code}},
                        # module_name 是硬编码的
                        {'term': {'module_name': 'default'}},
                        {'bool': {'must_not': [{'terms': {'stream': ['stderr', 'stdout']}}]}},
                        {'term': {'json.trace_id': 'foo'}},
                    ]
                }
            },
            'sort': [{'@timestamp': {'order': 'desc'}}],
            'size': 200,
            'from': 0,
        }

    def test_list(self, sys_api_client, bk_plugin_app):
        url = f"/sys/api/bk_plugins/{bk_plugin_app.code}/logs/?trace_id=foo&scroll_id=bar"
        with mock.patch("paasng.bk_plugins.bk_plugins.logging.instantiate_log_client") as client_factory:
            client_factory().execute_scroll_search.return_value = (
                Response(
                    Search(),
                    {
                        "hits": {
                            "hits": [
                                {
                                    "fields": {
                                        "@timestamp": 1,
                                        "json": {"message": "foo"},
                                        "one": {"two": {"three": "four"}},
                                        "region": bk_plugin_app.region,
                                        "app_code": bk_plugin_app.code,
                                        "environment": "stag",
                                        "process_id": "1234567",
                                        "stream": "foo",
                                        "pod_name": "bar",
                                    },
                                    "highlight": {"json.message": ["[bk-mark]", "???", "[/bk-mark]"]},
                                }
                            ]
                        },
                        "_scroll_id": "scroll_id",
                    },
                ),
                0,
            )
            response = sys_api_client.get(url)

        assert response.data["total"] == 0
        assert response.data["scroll_id"] == "scroll_id"
        assert response.data["logs"] == [
            {
                # 至少需要确保以下字段正常
                # plugin_code -> app.code
                # environment
                # process_id
                # stream
                # message
                # detail
                # ts
                'timestamp': 1,
                'message': '[bk-mark]???[/bk-mark]',
                'raw': {
                    # 不在白名单内的字段, 不返回
                    # "@timestamp": 1,
                    # "one.two.three": "four",
                    'json.message': '[bk-mark]???[/bk-mark]',
                    'region': bk_plugin_app.region,
                    'app_code': bk_plugin_app.code,
                    'environment': 'stag',
                    'process_id': '1234567',
                    'stream': 'foo',
                    'pod_name': 'bar',
                    'module_name': None,
                    'ts': '1970-01-01 08:00:01',
                },
                'detail': {
                    # 不在白名单内的字段, 不返回
                    # "@timestamp": 1,
                    # "one.two.three": "four",
                    'json.message': '[bk-mark]???[/bk-mark]',
                    'region': bk_plugin_app.region,
                    'app_code': bk_plugin_app.code,
                    'environment': 'stag',
                    'process_id': '1234567',
                    'stream': 'foo',
                    'pod_name': 'bar',
                    'module_name': None,
                    'ts': '1970-01-01 08:00:01',
                },
                'plugin_code': bk_plugin_app.code,
                'environment': 'stag',
                'process_id': '1234567',
                'stream': 'foo',
                'ts': '1970-01-01 08:00:01',
            }
        ]
