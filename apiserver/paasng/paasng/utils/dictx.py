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

from functools import reduce
from typing import Any, Dict, List, Union


def get_items(obj: Dict[str, Any], paths: Union[List[str], str], default: Any = None) -> Any:
    """
    根据指定的路径从字典中获取对应的值

    :param obj: 字典类型对象
    :param paths: ['foo', 'bar'] 或 ".foo.bar" 或 "foo.bar"
    :param default: 默认值
    :return: 指定路径的值 或 默认值
    """
    if not isinstance(obj, Dict):
        raise TypeError("only support get items from dict object!")

    if isinstance(paths, str):
        paths = paths.strip(".").split(".")

    try:
        return reduce(lambda d, k: d[k], paths, obj)
    except (KeyError, IndexError, TypeError):
        return default


def set_items(obj: Dict[str, Any], paths: List[str] | str, value: Any) -> None:
    """
    根据指定的路径为字典的某个 key 赋值

    :param obj: 字典类型对象
    :param paths: ['foo', 'bar'] 或 ".foo.bar" 或 "foo.bar"
    :param value: 待赋的值
    """
    if not isinstance(obj, Dict):
        raise TypeError("only support set items to dict object!")

    if isinstance(paths, str):
        paths = paths.strip(".").split(".")

    # 最深层一个 dict 对象
    leaf_obj = reduce(lambda d, k: d[k], paths[:-1], obj)
    leaf_obj[paths[-1]] = value


def exist_key(obj: Dict[str, Any], paths: List[str] | str) -> bool:
    """
    检查指定的路径对应的键是否存在

    :param obj: 字典类型对象
    :param paths: ['foo', 'bar'] 或 ".foo.bar" 或 "foo.bar"
    :return: exists
    """
    if not isinstance(obj, Dict):
        raise TypeError("only support check exist key in dict object!")

    if isinstance(paths, str):
        paths = paths.strip(".").split(".")

    try:
        reduce(lambda d, k: d[k], paths, obj)
    except (KeyError, IndexError, TypeError):
        return False

    return True
