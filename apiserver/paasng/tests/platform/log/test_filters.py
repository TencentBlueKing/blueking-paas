# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import pytest
from elasticsearch_dsl import Search

from paasng.platform.log.filters import AppLogFilter, BaseAppFilter


class TestAppFilter:
    @pytest.mark.parametrize(
        "base_info,fields_info,mappings,expected",
        [
            (
                ["default", "fake", "backend"],
                AppLogFilter.fields,
                {},
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {'term': {'app_code': 'fake'}},
                                {'term': {'module_name': 'backend'}},
                                {'term': {'region': 'default'}},
                            ]
                        }
                    }
                },
            ),
            (
                ["default", "fake", "backend"],
                [
                    {
                        "title": "app_code",
                        "chinese_name": "app_code",
                        "query_term": "app_code",
                        "is_multiple": True,
                    },
                    {
                        "title": "region",
                        "chinese_name": "region",
                        "query_term": "region",
                        "is_multiple": False,
                    },
                ],
                {"app_code": {"type": "text"}, "region": {"type": "keyword"}},
                {
                    'query': {
                        'bool': {
                            'filter': [
                                {'terms': {'app_code.keyword': 'fake'}},
                                {'term': {'region': 'default'}},
                            ]
                        }
                    }
                },
            ),
        ],
    )
    def test_filter_by_app(self, base_info, fields_info, mappings, expected):
        app_filter = BaseAppFilter(*base_info)
        app_filter.fields = fields_info
        fake_query = Search()
        assert app_filter.filter_by_app(fake_query, mappings).to_dict() == expected

    @pytest.mark.parametrize(
        "base_info,fields_info",
        [
            (
                ["default", "fake", "backend"],
                [
                    {
                        "title": "EngineAppName",
                        "chinese_name": "Engine应用名",
                        "query_term": "xxxx",
                    }
                ],
            )
        ],
    )
    def test_filter_by_app_unknown(self, base_info, fields_info):
        app_filter = BaseAppFilter(*base_info)
        app_filter.fields = fields_info
        fake_query = Search()
        with pytest.raises(AttributeError):
            app_filter.filter_by_app(fake_query, {})

    @pytest.mark.parametrize(
        "custom_name, custom_func, expected",
        [
            (
                "xxxx",
                lambda: "hahaha",
                {'query': {'bool': {'filter': [{'terms': {'xxxx': 'hahaha'}}]}}},
            ),
            (
                "ooooo",
                lambda: "uuuu",
                {'query': {'bool': {'filter': [{'terms': {'ooooo': 'uuuu'}}]}}},
            ),
        ],
    )
    def test_filter_by_app_custom(self, custom_name, custom_func, expected):
        app_filter = BaseAppFilter("default", "fake", "backend")
        app_filter.fields = [
            {"title": custom_name, "chinese_name": custom_name, "query_term": custom_name, "is_multiple": True}
        ]
        setattr(app_filter, f"get_field_{custom_name}_value", custom_func)
        fake_query = Search()
        assert app_filter.filter_by_app(fake_query, {}).to_dict() == expected
