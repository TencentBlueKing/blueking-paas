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
from typing import Generator, List

from elasticsearch_dsl import Search

from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.modules.models import Module

from .constants import ESField


class BaseAppFilter:

    fields: List[dict] = []

    def __init__(self, region: str, app_code: str, module_name: str):
        self.region = region
        self.app_code = app_code
        self.module_name = module_name

    def filter_by_app(self, query: Search, mappings: dict) -> Search:
        """为搜索增加应用相关过滤"""
        for f in self.get_es_fields():
            if getattr(self, f"get_field_{f.query_term}_value", None):
                query_value = getattr(self, f"get_field_{f.query_term}_value")()
            else:
                query_value = getattr(self, f.query_term)

            query = query.filter("terms" if f.is_multiple else "term", **{f.get_es_term(mappings): query_value})

        return query

    def get_es_fields(self) -> Generator[ESField, None, None]:
        """根据 fields 信息组装 ESField 对象列表"""
        for f in self.fields:
            yield ESField.parse_obj(f)


class AppLogFilter(BaseAppFilter):
    """应用日志过滤器"""

    fields = [
        {
            "title": "AppCode",
            "chinese_name": "应用 Code",
            "query_term": "app_code",
        },
        {
            "title": "ModuleName",
            "chinese_name": "模块名",
            "query_term": "module_name",
        },
        {
            "title": "Region",
            "chinese_name": "版本",
            "query_term": "region",
        },
    ]


class AppAccessLogFilter(BaseAppFilter):
    """应用访问日志过滤器"""

    fields = [
        {
            "title": "EngineAppName",
            "chinese_name": "Engine应用名",
            "query_term": "engine_app_name",
            "is_multiple": True,
        },
    ]

    def get_field_engine_app_name_value(self) -> List[str]:
        # 默认请求预发布&生产环境的日志，不作环境过滤
        return [
            x.replace("_", "0us0")
            for x in ModuleInitializer(
                Module.objects.get(application__code=self.app_code, name=self.module_name)
            ).list_engine_app_names()
        ]
