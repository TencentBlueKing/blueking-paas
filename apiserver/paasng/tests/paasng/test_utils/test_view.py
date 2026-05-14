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

import json
from io import BytesIO

import pytest
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from paasng.utils.views import (
    ERROR_CODE_NUM_HEADER,
    BkStandardApiJSONRenderer,
    HookChain,
    one_line_error,
    save_uploaded_file,
    validate_safe_filename,
)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ValidationError("foo"), "foo"),
        (ValidationError({"foo": [ErrorDetail("err1"), ErrorDetail("err2")]}), "foo: err1"),
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
    ("hooks", "expected"),
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
        ("resp", "result"),
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
                    headers={ERROR_CODE_NUM_HEADER: "4987"},
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
        raw_result = BkStandardApiJSONRenderer().render(resp.data, renderer_context={"response": resp})
        assert json.loads(raw_result) == result


def make_permission():
    class Permission(BasePermission): ...

    return Permission


class _FakeUploadedFile:
    """用于测试的最小化 UploadedFile 替代品，仅暴露 name 和 read 接口。"""

    def __init__(self, name: str, content: bytes = b""):
        self.name = name
        self._buf = BytesIO(content)

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size) if size != -1 else self._buf.read()


class TestValidateSafeFilename:
    @pytest.mark.parametrize("name", ["package.tar.gz", "a.tgz", "name with space.tar"])
    def test_valid(self, name):
        assert validate_safe_filename(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "",
            ".",
            "..",
            "../evil.tar.gz",
            "../../evil.tar.gz",
            "dir/package.tar.gz",
            "..\\evil.tar.gz",
            "dir\\package.tar.gz",
            "/tmp/evil.tar.gz",
            "/etc/passwd",
            "C:\\tmp\\evil.tar.gz",
        ],
    )
    def test_invalid(self, name):
        with pytest.raises(ValidationError):
            validate_safe_filename(name)


class TestSaveUploadedFile:
    def test_normal_filename_writes_inside_parent(self, tmp_path):
        fp = _FakeUploadedFile("package.tar.gz", b"hello")
        target = save_uploaded_file(fp, tmp_path)

        assert target == (tmp_path / "package.tar.gz").resolve()
        assert target.read_bytes() == b"hello"

    @pytest.mark.parametrize(
        "name",
        [
            "../../evil.tar.gz",
            "/tmp/evil.tar.gz",
            "..\\evil.tar.gz",
            "C:\\tmp\\evil.tar.gz",
            "dir/package.tar.gz",
            "",
            ".",
            "..",
        ],
    )
    def test_reject_unsafe_filenames(self, tmp_path, name):
        fp = _FakeUploadedFile(name, b"payload")
        with pytest.raises(ValidationError):
            save_uploaded_file(fp, tmp_path)

        # 父目录之外不应留下任何被写入的文件
        assert list(tmp_path.iterdir()) == []

    def test_invalid_file_object_raises_type_error(self, tmp_path):
        class _NoRead:
            name = "x.tar"

        with pytest.raises(TypeError):
            save_uploaded_file(_NoRead(), tmp_path)

    def test_chunks_method_is_used_when_available(self, tmp_path):
        class _Chunked:
            name = "package.tar.gz"

            def __init__(self):
                self.chunks_called = False

            def chunks(self):
                self.chunks_called = True
                yield b"hel"
                yield b"lo"

            def read(self, size=-1):
                raise AssertionError("read should not be called when chunks() is available")

        fp = _Chunked()
        target = save_uploaded_file(fp, tmp_path)
        assert fp.chunks_called is True
        assert target.read_bytes() == b"hello"
