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
from typing import Any, Dict


def dict_to_camel(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts dict keys from snake case to camel case.

    :param data: dict which keys are snake case string.
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
    words = snake_string.split("_")

    return words[0] + "".join(word.title() for word in words[1:])
