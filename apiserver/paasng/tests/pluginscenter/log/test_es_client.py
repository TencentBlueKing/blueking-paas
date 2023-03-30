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

from paasng.pluginscenter.log.client import ESLogClient
from paasng.utils.es_log.models import FieldFilter


@pytest.mark.parametrize(
    "nested_name, mapping, expected",
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
    assert ESLogClient._clean_property(nested_name, mapping) == expected
