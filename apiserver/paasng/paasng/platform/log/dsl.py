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
from typing import Dict, List

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# DSL 建模
class DSLQueryItem(BaseModel):
    """简化的 dsl-query 结构
    目前只支持: query_string/terms 两种查询方式
    :param query_string: 使用 ES 的 query_string 搜索
    :param terms: 精准匹配(根据 field 过滤 的场景)
    :param exclude: 精确过滤(根据 field 过滤 的场景)
    """

    query_string: str = Field(None, description="使用 `query_string` 语法进行搜索")
    terms: Dict[str, List[str]] = Field({}, description="多值精准匹配")
    exclude: Dict[str, List[str]] = Field({}, description="terms取反, 非标准 DSL")


class SimpleDomainSpecialLanguage(BaseModel):
    """简化的 dsl 结构, 前端查询日志时的查询协议

    :param query: 日志查询条件
    :param sort: 日志排序条件
    """

    query: DSLQueryItem
    sort: Dict = Field(default_factory=dict, description='排序，e.g. {"response_time": "desc", "other": "asc"}')
