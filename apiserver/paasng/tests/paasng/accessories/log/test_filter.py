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

from typing import Dict

import pytest
from elasticsearch_dsl import Search

from paasng.accessories.log.filters import (
    EnvFilter,
    ESFilter,
    ModuleFilter,
    _clean_property,
    count_filters_options_from_agg,
    count_filters_options_from_logs,
)
from paasng.accessories.log.models import ElasticSearchParams
from paasng.utils.es_log.models import FieldFilter
from paasng.utils.es_log.search import SmartSearch

pytestmark = pytest.mark.django_db


@pytest.fixture()
def all_filters() -> Dict[str, FieldFilter]:
    return {
        "foo": FieldFilter(name="foo", key="foo.keyword"),
        "bar": FieldFilter(name="bar", key="bar"),
        "b.a.z": FieldFilter(name="b.a.z", key="b.a.z"),
    }


@pytest.mark.parametrize(
    ("aggregations", "expected"),
    [
        (
            {"foo": {"buckets": [{"key": "example"}, {"key": "another example"}]}},
            {
                "foo": FieldFilter(
                    name="foo", key="foo.keyword", options=[("example", "50.00%"), ("another example", "50.00%")]
                ),
                "bar": FieldFilter(name="bar", key="bar"),
                "b.a.z": FieldFilter(name="b.a.z", key="b.a.z"),
            },
        ),
        (
            # 测试不存在的 key 会被忽略
            {
                "foo": {"buckets": [{"key": "example"}, {"key": "another example"}]},
                "b.a.r": {"buckets": [{"key": "example"}, {"key": "another example"}]},
            },
            {
                "foo": FieldFilter(
                    name="foo", key="foo.keyword", options=[("example", "50.00%"), ("another example", "50.00%")]
                ),
                "bar": FieldFilter(name="bar", key="bar"),
                "b.a.z": FieldFilter(name="b.a.z", key="b.a.z"),
            },
        ),
    ],
)
def test_count_filters_options_from_agg(all_filters, aggregations, expected):
    assert count_filters_options_from_agg(aggregations, all_filters) == expected


@pytest.mark.parametrize(
    ("logs", "expected"),
    [
        ([], {}),
        (
            [{"foo": "1", "bar": "1", "b": {"a": {"z": "1"}}}],
            {
                "foo": FieldFilter(name="foo", key="foo.keyword", options=[("1", "100.00%")], total=1),
                "bar": FieldFilter(name="bar", key="bar", options=[("1", "100.00%")], total=1),
                "b.a.z": FieldFilter(name="b.a.z", key="b.a.z", options=[("1", "100.00%")], total=1),
            },
        ),
        (
            [{"foo": "1", "bar": "1", "b": {"a": {"z": "1"}}}, {"foo": "1", "bar": "2"}],
            {
                "foo": FieldFilter(name="foo", key="foo.keyword", options=[("1", "100.00%")], total=2),
                "bar": FieldFilter(name="bar", key="bar", options=[("1", "50.00%"), ("2", "50.00%")], total=2),
                "b.a.z": FieldFilter(name="b.a.z", key="b.a.z", options=[("1", "100.00%")], total=1),
            },
        ),
    ],
)
def test_count_filters_options_from_logs(all_filters, logs, expected):
    assert count_filters_options_from_logs(logs, all_filters) == expected


def test_count_filters_options_from_logs_when_options_has_been_set(all_filters):
    all_filters["foo"].options = [("stag", "100.00%")]
    logs = [{"foo": "stag"}, {"foo": "prod"}]
    # 理论上不可能出现这个场景(因为 Agg 统计会被日志采样要精准)
    # 单测只是把代码的边界行为写清楚
    assert count_filters_options_from_logs(logs, all_filters) == {
        "foo": FieldFilter(name="foo", key="foo.keyword", options=[("stag", "100.00%"), ("prod", "50.00%")], total=2)
    }


# 设置 app code, module name, engine app name 以简化单测样例复杂度
@pytest.fixture()
def bk_app(bk_app):
    bk_app.code = "foo-app"
    bk_app.save()
    return bk_app


@pytest.fixture()
def bk_module(bk_module):
    bk_module.name = "foo-module"
    bk_module.save()
    return bk_module


@pytest.fixture()
def env(bk_stag_env):
    return bk_stag_env


@pytest.fixture()
def search():
    # 避免引入 time_range 相关的过滤语句
    search = SmartSearch.__new__(SmartSearch)
    search.search = Search()
    return search


class TestESFilter:
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
    def test_filter_by_builtin_filters(self, search, params, expected):
        assert ESFilter(params).filter_by_builtin_filters(search).to_dict() == expected

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
    def test_filter_by_builtin_excludes(self, search, params, expected):
        assert ESFilter(params).filter_by_builtin_excludes(search).to_dict() == expected


class TestEnvFilter:
    @pytest.fixture()
    def engine_app(self, env):
        engine_app = env.get_engine_app()
        # 测试下划线转换成 0us0 的逻辑
        engine_app.name = "bkapp-foo_bar-stag"
        engine_app.save()
        return engine_app

    @pytest.mark.parametrize(
        ("params", "expected"),
        [
            (
                ElasticSearchParams(indexPattern="", termTemplate={"app_code": "{{ app_code }}"}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"app_code": "foo-app"}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={"module_name": "{{ module_name }}"}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"module_name": "foo-module"}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={"engine_app_name": "{{ engine_app_name }}"}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"engine_app_name": "bkapp-foo0us0bar-stag"}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(
                    indexPattern="", termTemplate={"engine_app_name": "{{ engine_app_names | tojson }}"}
                ),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"terms": {"engine_app_name": ["bkapp-foo0us0bar-stag"]}},
                            ]
                        }
                    }
                },
            ),
        ],
    )
    def test_filter_by_env(self, engine_app, search, params, expected):
        assert EnvFilter(engine_app.env, params).filter_by_env(search).to_dict() == expected


class TestModuleFilter:
    @pytest.fixture()
    def stag_engine_app(self, bk_stag_env):
        engine_app = bk_stag_env.get_engine_app()
        # 测试下划线转换成 0us0 的逻辑
        engine_app.name = "bkapp-foo_bar-stag"
        engine_app.save()
        return engine_app

    @pytest.fixture()
    def prod_engine_app(self, bk_prod_env):
        engine_app = bk_prod_env.get_engine_app()
        # 测试下划线转换成 0us0 的逻辑
        engine_app.name = "bkapp-foo_bar-prod"
        engine_app.save()
        return engine_app

    @pytest.mark.parametrize(
        ("params", "expected"),
        [
            (
                ElasticSearchParams(indexPattern="", termTemplate={"app_code": "{{ app_code }}"}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"app_code": "foo-app"}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={"module_name": "{{ module_name }}"}),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"module_name": "foo-module"}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(
                    indexPattern="", termTemplate={"engine_app_name": "{{ engine_app_names | tojson }}"}
                ),
                {
                    "query": {
                        "bool": {
                            "filter": [
                                {"terms": {"engine_app_name": ["bkapp-foo0us0bar-prod", "bkapp-foo0us0bar-stag"]}},
                            ]
                        }
                    }
                },
            ),
        ],
    )
    def test_filter_by_module(self, bk_module, stag_engine_app, prod_engine_app, search, params, expected):
        assert ModuleFilter(bk_module, params).filter_by_module(search).to_dict() == expected

    def test_render_failed(self, bk_module, stag_engine_app, prod_engine_app, search):
        params = ElasticSearchParams(indexPattern="", termTemplate={"engine_app_name": "{{ engine_app_name }}"})
        with pytest.raises(ValueError, match=r".*template must be using.*"):
            ModuleFilter(bk_module, params).filter_by_module(search)


@pytest.mark.parametrize(
    ("nested_name", "mapping", "expected"),
    [
        (
            ["a"],
            {"properties": {"a": {"type": "text"}, "b": {"type": "int"}}},
            [FieldFilter(name="a.a", key="a.a.keyword"), FieldFilter(name="a.b", key="a.b")],
        ),
        (
            ["a", "b", "c"],
            {
                "properties": {
                    "d": {"properties": {"e": {"properties": {"f": {"properties": {"g": {"type": "text"}}}}}}}
                }
            },
            [FieldFilter(name="a.b.c.d.e.f.g", key="a.b.c.d.e.f.g.keyword")],
        ),
        # invalid
        (
            ["a"],
            {"a": {"type": "text"}, "b": {"type": "int"}},
            [],
        ),
    ],
)
def test_clean_property(nested_name, mapping, expected):
    assert _clean_property(nested_name, mapping) == expected
