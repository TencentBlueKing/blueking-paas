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

import pytest
from elasticsearch_dsl import Search

from paasng.bk_plugins.pluginscenter.definitions import ElasticSearchParams
from paasng.bk_plugins.pluginscenter.log.filters import ElasticSearchFilter
from paasng.utils.es_log.search import SmartSearch

pytestmark = pytest.mark.django_db


class TestElasticSearchFilter:
    @pytest.fixture()
    def plugin(self, plugin):
        # 修改 plugin.id 确保单测
        plugin.id = "foo"
        return plugin

    @pytest.fixture()
    def search(self):
        # 避免引入 time_range 相关的过滤语句
        search = SmartSearch.__new__(SmartSearch)
        search.search = Search()
        return search

    @pytest.mark.parametrize(
        ("params", "expected"),
        [
            (
                ElasticSearchParams(indexPattern="", termTemplate={"plugin_id": "{{ plugin_id }}"}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"plugin_id": "foo"}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={"engine_app_name": "bkapp-{{ plugin_id }}-prod"}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"engine_app_name": "bkapp-foo-prod"}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(
                    indexPattern="", termTemplate={"foo": "{{ plugin_id }}", "FOO": "{{ plugin_id | upper }}"}
                ),
                {"query": {"bool": {"filter": [{"term": {"foo": "foo"}}, {"term": {"FOO": "FOO"}}]}}},
            ),
        ],
    )
    def test_filter_by_plugin(self, plugin, search, params, expected):
        assert ElasticSearchFilter(plugin, params).filter_by_plugin(search).to_dict() == expected

    @pytest.mark.parametrize(
        ("params", "expected"),
        [
            (
                ElasticSearchParams(indexPattern="", termTemplate={}, builtinFilters={"a": "a", "b": "b"}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"a": "a"}},
                                {"term": {"b": "b"}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={}, builtinFilters={"a": "a", "b": ["b", "B"]}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"a": "a"}},
                                {"terms": {"b": ["b", "B"]}},
                            ]
                        }
                    }
                },
            ),
        ],
    )
    def test_filter_by_builtin_filters(self, plugin, search, params, expected):
        assert ElasticSearchFilter(plugin, params).filter_by_builtin_filters(search).to_dict() == expected

    @pytest.mark.parametrize(
        ("params", "expected"),
        [
            (
                ElasticSearchParams(indexPattern="", termTemplate={}, builtinExcludes={"a": "a", "b": "b"}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {
                                    "bool": {
                                        "must_not": [
                                            {"term": {"a": "a"}},
                                        ]
                                    }
                                },
                                {
                                    "bool": {
                                        "must_not": [
                                            {"term": {"b": "b"}},
                                        ]
                                    }
                                },
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={}, builtinExcludes={"a": "a", "b": ["b", "B"]}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {
                                    "bool": {
                                        "must_not": [
                                            {"term": {"a": "a"}},
                                        ]
                                    }
                                },
                                {
                                    "bool": {
                                        "must_not": [
                                            {"terms": {"b": ["b", "B"]}},
                                        ]
                                    }
                                },
                            ]
                        }
                    }
                },
            ),
        ],
    )
    def test_filter_by_builtin_excludes(self, plugin, search, params, expected):
        assert ElasticSearchFilter(plugin, params).filter_by_builtin_excludes(search).to_dict() == expected
