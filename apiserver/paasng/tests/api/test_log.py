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
from elasticsearch_dsl.response import Hit

pytestmark = pytest.mark.django_db


class TestLegacyStructuredLogAPIView:
    def test_dsl(self, api_client, bk_app, bk_module):
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/structured/list/?time_range=1h"
        with mock.patch("paasng.platform.log.views.instantiate_log_client") as client_factory:
            client_factory().get_mappings.return_value = {"app_code": {"type": "text"}}
            # 无任何日志
            client_factory().execute_search.return_value = ([], 0)
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

        assert response.data["total"] == 0
        assert response.data["logs"] == []
        # 测试 dsl 的拼接 是否符合预期
        assert json.loads(response.data["dsl"]) == {
            'query': {
                'bool': {
                    'filter': [
                        {'range': {'@timestamp': {'gte': 'now-1h', 'lte': 'now'}}},
                        # mappings 返回类型是 text, 因此添加了 .keyword
                        {'term': {'app_code.keyword': bk_app.code}},
                        {'term': {'module_name': bk_module.name}},
                        {'bool': {'must_not': [{'terms': {'stream': ['stderr', 'stdout']}}]}},
                    ],
                    'must': [
                        {'query_string': {'query': 'query_string', 'analyze_wildcard': True}},
                        {'terms': {'terms': ['foo', 'bar']}},
                    ],
                    'must_not': [{'terms': {'exclude': ['foo', 'bar']}}],
                }
            },
            'sort': [{'ts': {'order': 'asc'}}],
            'size': 200,
            'from': 0,
            'highlight': {
                'fields': {'*': {'number_of_fragments': 0}, '*.*': {'number_of_fragments': 0}},
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
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/structured/list/?time_range=1h"
        with mock.patch("paasng.platform.log.views.instantiate_log_client") as client_factory:
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

        assert response.data["total"] == 0
        # 测试日志的解析是否符合预期
        assert response.data["logs"] == [
            {
                'timestamp': 1,
                # 高亮
                'message': '[bk-mark]???[/bk-mark]',
                'detail': {
                    '@timestamp': 1,
                    # 扁平化
                    'json.message': '[bk-mark]???[/bk-mark]',
                    'one.two.three': 'four',
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
            }
        ]
