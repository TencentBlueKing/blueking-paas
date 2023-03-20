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
import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, root_validator

from paasng.platform.log.constants import LOG_QUERY_FIELDS

logger = logging.getLogger(__name__)


# DSL 建模
class DSLQueryItem(BaseModel):
    """简化的 dsl-query 结构
    目前只支持: query_string/terms 两种查询方式
    query_string: 使用 ES 的 query_string 搜索
    terms: 精准匹配(根据 field 过滤 的场景)
    """

    query_string: str = Field(None, description="使用 `query_string` 语法进行搜索")
    terms: Dict[str, List[str]] = Field({}, description="多值精准匹配")
    exclude: Dict[str, List[str]] = Field({}, description="terms取反, 非标准 DSL")

    @root_validator(pre=True)
    @classmethod
    def transfer_query_term_to_es_term(cls, values: Dict):
        # 将 query_term 转换成 es_term
        terms = values.get("terms", {})
        exclude = values.get("exclude", {})

        for container in [terms, exclude]:
            for regular_field in LOG_QUERY_FIELDS:
                if regular_field.query_term in container:
                    v = container.pop(regular_field.query_term)
                    container[regular_field.query_term] = v
        return values


class SimpleDomainSpecialLanguage(BaseModel):
    """简化的 dsl 结构"""

    query: DSLQueryItem
    sort: Optional[Dict] = Field({}, description='排序，e.g. {"response_time": "desc", "other": "asc"}')

    def add_terms_conditions(self, **kwargs):
        kwargs = self.query.parse_obj(dict(terms=kwargs)).dict()
        self.query.terms.update(kwargs["terms"])
        return self

    def add_exclude_conditions(self, **kwargs):
        kwargs = self.query.parse_obj(dict(exclude=kwargs)).dict()
        self.query.exclude.update(kwargs["exclude"])
        return self

    def remove_terms_condition(self, key):
        return self.remove_conditions_core("terms", key)

    def remove_exclude_conditions(self, key):
        return self.remove_conditions_core("exclude", key)

    def remove_conditions_core(self, cond_type: str, key):
        if cond_type not in ["terms", "exclude"]:
            raise NotImplementedError

        if key in getattr(self.query, cond_type):
            getattr(self.query, cond_type).pop(key, None)

        return self

    def remove_regular_conditions(self, mappings: dict):
        for regular_field in LOG_QUERY_FIELDS:
            self.remove_terms_condition(regular_field.get_es_term(mappings))
            self.remove_terms_condition(regular_field.query_term)
        return self
