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

from paasng.utils.dictx import get_items


@pytest.mark.parametrize(
    ("obj", "paths", "default", "expected"),
    [
        ({"a": {"b": {"c": 1}}}, "a.b.c", None, 1),
        ({"a": {"b": {"c": 1}}}, ".a.b.c", None, 1),
        ({"a": {"b": {"c": 1}}}, ["a", "b", "c"], None, 1),
        ({"a": {"b": {"c": None}}}, "a.b.c", "default", None),
        ({"a": {"b": {}}, "c": 2}, "c", "default", 2),
        ({"a": {"b": {}}, "c": 2}, "d", "default", "default"),
        ({}, "a", "default", "default"),
        ({"a": 1}, "", "default", "default"),
        ({"a": 1}, "a", "default", 1),
    ],
)
def test_get_items(obj, paths, default, expected):
    assert get_items(obj, paths, default) == expected


@pytest.mark.parametrize(
    ("obj", "paths", "default"),
    [
        (None, "a.b.c", None),
        (None, ["a", "b", "c"], None),
        (1, "a", "default"),
    ],
)
def test_get_items_exceptions(obj, paths, default):
    with pytest.raises(TypeError):
        get_items(obj, paths, default)  # type: ignore
