# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import json

import pytest
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.response import Response

from paasng.utils.views import ERROR_CODE_NUM_HEADER, BkStandardApiJSONRenderer, HookChain, one_line_error


@pytest.mark.parametrize(
    'error,expected',
    [
        (ValidationError('foo'), 'foo'),
        (ValidationError({'foo': [ErrorDetail('err1'), ErrorDetail('err2')]}), 'foo: err1'),
    ],
)
def test_one_line_error(error, expected):
    assert one_line_error(error) == expected


def dummy_hook(key, value):
    def hook(resp, view, request):
        resp[key] = value
        return resp

    return hook


@pytest.mark.parametrize(
    "hooks, expected",
    [
        (
            [
                dummy_hook(1, 1),
                dummy_hook(2, 2),
            ],
            {1: 1, 2: 2},
        ),
        (
            [
                dummy_hook(1, 1),
                dummy_hook(1, 2),
            ],
            {1: 2},
        ),
    ],
)
def test_hook_chain(hooks, expected):
    pre_hook = None
    for hook in hooks:
        pre_hook = HookChain(hook, pre_hook)

    assert pre_hook is not None
    assert pre_hook({}, None, None) == expected


class TestBkStandardApiJSONRenderer:
    @pytest.mark.parametrize(
        'resp,result',
        [
            # Successful response
            (Response([0, 1, 2], status=200), {"result": True, "data": [0, 1, 2], "code": 0, "message": ""}),
            # Client error with code and detail
            (
                Response({"code": "FOO", "detail": "foo error"}, status=400),
                {"result": False, "data": {}, "code": -1, "message": "foo error", "code_slug": "FOO"},
            ),
            # Client error with numeric code and detail
            (
                Response(
                    {"code": "FOO", "detail": "foo error with num"},
                    status=400,
                    headers={ERROR_CODE_NUM_HEADER: '4987'},
                ),
                {"result": False, "data": {}, "code": 4987, "message": "foo error with num", "code_slug": "FOO"},
            ),
            # Client error without any extra info
            (
                Response('""', status=404),
                {"result": False, "data": '""', "code": -1, "message": "Unknown error, please try again later"},
            ),
        ],
    )
    def test_render(self, resp, result):
        raw_result = BkStandardApiJSONRenderer().render(resp.data, renderer_context={'response': resp})
        assert json.loads(raw_result) == result
