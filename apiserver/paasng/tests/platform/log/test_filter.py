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
import pytest
from elasticsearch_dsl import Search

from paasng.platform.log.filters import EnvFilter, ESFilter, ModuleFilter
from paasng.platform.log.models import ElasticSearchParams
from paasng.utils.es_log.search import SmartSearch

pytestmark = pytest.mark.django_db


# 设置 app code, module name, engine app name 以简化单测样例复杂度
@pytest.fixture
def bk_app(bk_app):
    bk_app.code = "foo-app"
    bk_app.save()
    return bk_app


@pytest.fixture
def bk_module(bk_module):
    bk_module.name = "foo-module"
    bk_module.save()
    return bk_module


@pytest.fixture
def env(bk_stag_env):
    return bk_stag_env


@pytest.fixture
def search():
    # 避免引入 time_range 相关的过滤语句
    search = SmartSearch.__new__(SmartSearch)
    search.search = Search()
    return search


class TestESFilter:
    @pytest.mark.parametrize(
        "params, expected",
        [
            (
                ElasticSearchParams(indexPattern="", termTemplate={}, builtinFilters={"a": "a", "b": "b"}),
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {'term': {'a': 'a'}},
                                {'term': {'b': 'b'}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={}, builtinFilters={"a": "a", "b": ["b", "B"]}),
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {'term': {'a': 'a'}},
                                {'terms': {'b': ["b", "B"]}},
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
        "params, expected",
        [
            (
                ElasticSearchParams(indexPattern="", termTemplate={}, builtinExcludes={"a": "a", "b": "b"}),
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {
                                    'bool': {
                                        'must_not': [
                                            {'term': {'a': 'a'}},
                                        ]
                                    }
                                },
                                {
                                    'bool': {
                                        'must_not': [
                                            {'term': {'b': 'b'}},
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
                    'query': {
                        'bool': {
                            'filter': [
                                {
                                    'bool': {
                                        'must_not': [
                                            {'term': {'a': 'a'}},
                                        ]
                                    }
                                },
                                {
                                    'bool': {
                                        'must_not': [
                                            {'terms': {'b': ['b', 'B']}},
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
    @pytest.fixture
    def engine_app(self, env):
        engine_app = env.get_engine_app()
        engine_app.name = "bkapp-foo_bar-stag"
        engine_app.save()
        return engine_app

    @pytest.mark.parametrize(
        "params, expected",
        [
            (
                ElasticSearchParams(indexPattern="", termTemplate={"app_code": "{{ app_code }}"}),
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {'term': {'app_code': 'foo-app'}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={"module_name": "{{ module_name }}"}),
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {'term': {'module_name': 'foo-module'}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={"engine_app_name": "{{ engine_app_name }}"}),
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {'term': {'engine_app_name': 'bkapp-foo0us0bar-stag'}},
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
                    'query': {
                        'bool': {
                            'filter': [
                                {'terms': {'engine_app_name': ['bkapp-foo0us0bar-stag']}},
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
    @pytest.fixture
    def stag_engine_app(self, bk_stag_env):
        engine_app = bk_stag_env.get_engine_app()
        engine_app.name = "bkapp-foo_bar-stag"
        engine_app.save()
        return engine_app

    @pytest.fixture
    def prod_engine_app(self, bk_prod_env):
        engine_app = bk_prod_env.get_engine_app()
        engine_app.name = "bkapp-foo_bar-prod"
        engine_app.save()
        return engine_app

    @pytest.mark.parametrize(
        "params, expected",
        [
            (
                ElasticSearchParams(indexPattern="", termTemplate={"app_code": "{{ app_code }}"}),
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {'term': {'app_code': 'foo-app'}},
                            ]
                        }
                    }
                },
            ),
            (
                ElasticSearchParams(indexPattern="", termTemplate={"module_name": "{{ module_name }}"}),
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {'term': {'module_name': 'foo-module'}},
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
                    'query': {
                        'bool': {
                            'filter': [
                                {'terms': {'engine_app_name': ['bkapp-foo0us0bar-prod', 'bkapp-foo0us0bar-stag']}},
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
        with pytest.raises(ValueError):
            ModuleFilter(bk_module, params).filter_by_module(search)
