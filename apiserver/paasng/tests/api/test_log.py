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
from django.test.utils import override_settings
from django_dynamic_fixture import G
from elasticsearch_dsl.response import Hit

from paasng.accessories.log.models import CustomCollectorConfig
from paasng.accessories.log.shim.setup_bklog import build_custom_collector_config_name
from paasng.infras.bkmonitorv3.models import BKMonitorSpace

pytestmark = pytest.mark.django_db


class TestModuleStructuredLogAPIView:
    def test_dsl(self, api_client, bk_app, bk_module):
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/structured/list/?time_range=1h"
        with mock.patch("paasng.accessories.log.views.logs.instantiate_log_client") as client_factory:
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
                    "sort": {"some-field": "asc"},
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
            'sort': [{'@timestamp': {'order': 'desc'}, 'some-field': {'order': 'asc'}}],
            'size': 100,
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
                "timestamp": 1,
                # # 高亮
                "message": "[bk-mark]???[/bk-mark]",
                "detail": {
                    # 不在白名单内的字段, 不返回
                    # "@timestamp": 1,
                    # "one.two.three": "four",
                    "json.message": "[bk-mark]???[/bk-mark]",
                    "region": bk_app.region,
                    "app_code": bk_app.code,
                    "module_name": "default",
                    "environment": "stag",
                    "process_id": "1234567",
                    "stream": "foo",
                    "pod_name": "bar",
                },
                "region": bk_app.region,
                "app_code": bk_app.code,
                # 没有 module_name
                "environment": "stag",
                "process_id": "1234567",
                "stream": "foo",
            }
        ]


class TestCustomCollectorConfigViewSet:
    @pytest.fixture
    def cfg_maker(self, bk_module):
        def maker(**kwargs):
            return G(CustomCollectorConfig, module=bk_module, **kwargs)

        return maker

    @pytest.fixture
    def builtin_json_cfg(self, bk_module, cfg_maker):
        return cfg_maker(
            name_en=build_custom_collector_config_name(bk_module, type="json"),
            log_type="json",
        )

    @pytest.fixture
    def builtin_stdout_cfg(self, bk_module, cfg_maker):
        return cfg_maker(
            name_en=build_custom_collector_config_name(bk_module, type="stdout"),
            log_type="stdout",
        )

    @pytest.fixture(autouse=True)
    def bkmonitor_space(self, bk_app):
        return G(BKMonitorSpace, application=bk_app)

    def test_list(self, api_client, bk_app, bk_module, builtin_json_cfg, builtin_stdout_cfg, cfg_maker):
        cfg_maker()

        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/custom-collector/"
        resp = api_client.get(url)
        assert len(resp.data) == 3
        assert not resp.data[0]["is_builtin"]
        assert resp.data[1]["is_builtin"]
        assert resp.data[2]["is_builtin"]

    @pytest.fixture
    def apigw_client(self):
        with mock.patch("paasng.infras.bk_log.client.APIGWClient") as cls, override_settings(ENABLE_BK_LOG_APIGW=True):
            yield cls().api

    def test_list_metadata(self, api_client, bk_app, bk_module, apigw_client, bkmonitor_space):
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/custom-collector-metadata/"

        apigw_client.databus_list_collectors.return_value = {
            "result": True,
            "data": [
                {
                    "collector_config_name_en": build_custom_collector_config_name(bk_module, type="stdout"),
                    "collector_config_name": build_custom_collector_config_name(bk_module, type="stdout"),
                    "custom_type": "log",
                    "collector_config_id": 1,
                    "index_set_id": 0,
                    "bk_data_id": 0,
                },
                {
                    "collector_config_name_en": build_custom_collector_config_name(bk_module, type="json"),
                    "collector_config_name": build_custom_collector_config_name(bk_module, type="json"),
                    "custom_type": "log",
                    "collector_config_id": 2,
                    "index_set_id": 0,
                    "bk_data_id": 0,
                },
                {
                    "collector_config_name_en": "test",
                    "collector_config_name": "测试",
                    "custom_type": "log",
                    "collector_config_id": 3,
                    "index_set_id": 0,
                    "bk_data_id": 0,
                },
            ],
        }

        resp = api_client.get(url)
        assert "url" in resp.data
        options = resp.data["options"]
        assert len(options) == 3
        assert options[0]["is_builtin"]
        assert options[1]["is_builtin"]
        assert not options[2]["is_builtin"]

    def test_insert_success(self, api_client, bk_app, bk_module, apigw_client, bkmonitor_space):
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/custom-collector/"
        assert len(api_client.get(url).data) == 0

        apigw_client.databus_list_collectors.return_value = {
            "result": True,
            "data": [
                {
                    "collector_config_name_en": "test",
                    "collector_config_name": "测试",
                    "custom_type": "log",
                    "collector_config_id": 3,
                    "index_set_id": 0,
                    "bk_data_id": 0,
                },
            ],
        }

        data = {"name_en": "test", "collector_config_id": 3, "log_paths": ["/a/b/c", "/foo/*"], "log_type": "json"}
        resp = api_client.post(url, data=data)
        assert resp.status_code == 200
        assert len(api_client.get(url).data) == 1

    def test_insert_failed(self, api_client, bk_app, bk_module, apigw_client, bkmonitor_space):
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/custom-collector/"
        assert len(api_client.get(url).data) == 0

        apigw_client.databus_list_collectors.return_value = {
            "result": True,
            "data": [],
        }

        data = {"name_en": "test", "collector_config_id": 3, "log_paths": ["/a/b/c", "/foo/*"], "log_type": "json"}
        resp = api_client.post(url, data=data)
        assert resp.status_code == 400
        assert resp.data["code"] == "CUSTOM_COLLECTOR_NOT_EXISTED"

    def test_update_success(self, api_client, bk_app, bk_module, apigw_client, cfg_maker, bkmonitor_space):
        cfg_maker(
            name_en="test",
            collector_config_id=3,
            log_paths=["/bar/*"],
            log_type="json",
        )
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/log/custom-collector/"
        existed = api_client.get(url).data
        assert len(existed) == 1
        assert existed[0]["name_en"] == "test"
        assert existed[0]["log_paths"] == ["/bar/*"]
        assert len(api_client.get(url).data) == 1

        apigw_client.databus_list_collectors.return_value = {
            "result": True,
            "data": [
                {
                    "collector_config_name_en": "test",
                    "collector_config_name": "测试",
                    "custom_type": "log",
                    "collector_config_id": 3,
                    "index_set_id": 0,
                    "bk_data_id": 0,
                },
            ],
        }
        data = {"name_en": "test", "collector_config_id": 3, "log_paths": ["/a/b/c", "/foo/*"], "log_type": "json"}
        assert api_client.post(url, data=data).status_code == 200

        cfg = CustomCollectorConfig.objects.get(module=bk_module, collector_config_id=3)
        assert cfg.log_paths == ["/a/b/c", "/foo/*"]
        assert cfg.log_type == "json"
