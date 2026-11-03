# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import pytest

from paas_wl.workloads.networking.ingress.models import TxtFile
from paas_wl.workloads.networking.ingress.txt_files.serializers import (
    MAX_CONTENT_BYTES,
    MAX_FILES_PER_ENV,
    TxtFileSLZ,
)

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def make_slz(env, instance=None, **data):
    data = {"path": "/verify.txt", "content": "abc", **data}
    return TxtFileSLZ(instance, data=data, context={"env": env})


@pytest.mark.parametrize(
    ("path", "valid"),
    [
        ("/MP_verify_a-B.1.txt", True),
        ("/a/verify.txt", False),
        ("/../verify.txt", False),
        ("/verify.txt?a=1", False),
        ("/verify.html", False),
    ],
)
def test_path(bk_stag_env, path, valid):
    assert make_slz(bk_stag_env, path=path).is_valid() is valid


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("  中文\tabc\r\ndef\n", "  中文\tabc\ndef\n"),
        ("price: $1", None),
        ("abc\x00", None),
        ("a" * (MAX_CONTENT_BYTES + 1), None),
    ],
)
def test_content(bk_stag_env, content, expected):
    slz = make_slz(bk_stag_env, content=content)
    assert slz.is_valid() is (expected is not None)
    if expected is not None:
        assert slz.validated_data["content"] == expected


def test_env_constraints(bk_stag_env):
    txt_file = TxtFile.objects.create(environment_id=bk_stag_env.id, path="/verify.txt", content="abc")
    assert make_slz(bk_stag_env).is_valid() is False
    assert make_slz(bk_stag_env, instance=txt_file).is_valid() is True

    TxtFile.objects.bulk_create(
        [TxtFile(environment_id=bk_stag_env.id, path=f"/{i}.txt", content="abc") for i in range(MAX_FILES_PER_ENV - 1)]
    )
    assert make_slz(bk_stag_env, path="/new.txt").is_valid() is False
