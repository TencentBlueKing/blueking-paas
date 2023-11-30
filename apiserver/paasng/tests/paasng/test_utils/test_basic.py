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

from paasng.utils.basic import first_true, unique_id_generator

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("data", "default", "ret"),
    [
        ([None, "foo"], None, "foo"),
        ([None, ""], None, None),
        ([None, ()], "bar", "bar"),
    ],
)
def test_first_true(data, default, ret):
    assert first_true(data, default=default) == ret


def test_unique_id_generator():
    val = unique_id_generator("foo")
    assert val != ""
    assert val.startswith("foo")
