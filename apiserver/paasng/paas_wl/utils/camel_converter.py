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
"""
该模块与 paasng.utils.camel_converter.py/paasng.platform.declarative.util 重复
因为 wl 不能引用 ng ，因此将其复制，未来考虑底层抽出后合并
"""

from typing import Any, Dict

from blue_krill.cubing_case import CommonCaseConvertor, CommonCaseRegexPatterns, shortcuts


def dict_to_camel(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts dict keys from snake case to camel case.

    :param data: dict which keys are snake case string.

    Note: 如果遇到特殊的缩写词, 需要单独额外处理
    ref: https://gocn.github.io/styleguide/docs/03-decisions/#%e7%bc%a9%e5%86%99%e8%af%8dinitialisms
    """
    converted: Dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(k, str):
            key = snake_to_camel(k)
        else:
            key = k

        if isinstance(v, dict):
            converted[key] = dict_to_camel(v)
        elif isinstance(v, list):
            converted[key] = [dict_to_camel(x) if isinstance(x, dict) else x for x in v]
        elif isinstance(v, tuple):
            converted[key] = tuple(dict_to_camel(x) if isinstance(x, dict) else x for x in v)
        else:
            converted[key] = data[k]

    return converted


def snake_to_camel(snake_string: str) -> str:
    """Converts a snake case string to camel case.

    :param snake_string: String in snake case format. For example my_variable.
    :return: The string in camel case format. For example myVariable.
    """
    convertor = CommonCaseConvertor([CommonCaseRegexPatterns.SNAKECASE])
    return convertor.to_lower_camel_case(snake_string)


def camel_to_snake_case(data: Any) -> Any:
    """convert all camel case field name to snake case, and return the converted obj"""
    if isinstance(data, dict):
        return {shortcuts.to_lower_snake_case(key): camel_to_snake_case(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [camel_to_snake_case(item) for item in data]
    return data
