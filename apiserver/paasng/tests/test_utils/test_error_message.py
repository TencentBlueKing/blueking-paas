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
from rest_framework.exceptions import ValidationError

from paasng.dev_resources.servicehub.remote.exceptions import GetClusterEgressInfoError
from paasng.utils.error_message import find_coded_error_message, find_innermost_exception, wrap_validation_error


@pytest.mark.parametrize(
    "exception, expected",
    [
        (GetClusterEgressInfoError("Detail Message"), "错误码: 4313021, 获取集群信息失败: Detail Message。"),
        (Exception("AAAAA"), None),
        pytest.param("unexpected", "", marks=pytest.mark.xfail(raises=ValueError)),
    ],
)
def test_find_coded_error_message(exception, expected):
    assert find_coded_error_message(exception) == expected


def a():
    raise Exception("A")


def b_in_a():
    try:
        a()
    except Exception as e:
        raise Exception("B") from e


def b():
    try:
        a()
    except Exception:
        raise Exception("B")


def c_in_b_in_a():
    try:
        b_in_a()
    except Exception as e:
        raise Exception("C") from e


def c_in_b():
    try:
        b()
    except Exception as e:
        raise Exception("C") from e


@pytest.mark.parametrize(
    "trigger, expected",
    [
        (a, Exception("A")),
        (b_in_a, Exception("A")),
        (c_in_b_in_a, Exception("A")),
        (b, Exception("B")),
        (c_in_b, Exception("B")),
    ],
)
def test_find_innermost_exception(trigger, expected):
    try:
        trigger()
    except Exception as e:
        assert str(find_innermost_exception(e)) == str(expected)


def test_wrap_validation_error_dict():
    wrapped_ext = wrap_validation_error(ValidationError(detail={'foo': 'required'}, code='bar'), 'parent')
    assert 'parent' in wrapped_ext.detail
    assert wrapped_ext.detail['parent']['foo'] == 'required'
    assert wrapped_ext.detail['parent']['foo'].code == 'bar'


def test_wrap_validation_error_list():
    wrapped_ext = wrap_validation_error(ValidationError(detail=['foo: required'], code='bar'), 'parent')
    assert wrapped_ext.detail[0] == '[parent] foo: required'
    assert wrapped_ext.detail[0].code == 'bar'


def test_wrap_validation_error_str():
    wrapped_ext = wrap_validation_error(ValidationError(detail='foo: required', code='bar'), 'parent')
    assert wrapped_ext.detail[0] == '[parent] foo: required'
    assert wrapped_ext.detail[0].code == 'bar'
