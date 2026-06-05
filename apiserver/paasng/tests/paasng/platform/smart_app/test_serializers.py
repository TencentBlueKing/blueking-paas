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
from django.core.files.uploadedfile import SimpleUploadedFile

from paasng.platform.smart_app.serializers import PackageStashRequestSLZ


class _RawNamedFile:
    def __init__(self, name):
        self.name = name
        self.size = 4

    def read(self, *args, **kwargs):
        return b"data"


class TestPackageStashRequestSLZ:
    def test_valid_filename_pass(self):
        package = SimpleUploadedFile("package.tar.gz", b"data")
        slz = PackageStashRequestSLZ(data={"package": package})
        assert slz.is_valid(), slz.errors

    @pytest.mark.parametrize(
        "name",
        [
            "../../evil.tar.gz",
            "/tmp/evil.tar.gz",
            "..\\evil.tar.gz",
            "C:\\tmp\\evil.tar.gz",
            "dir/package.tar.gz",
        ],
    )
    def test_unsafe_filename_rejected(self, name):
        package = _RawNamedFile(name)
        slz = PackageStashRequestSLZ(data={"package": package})
        assert not slz.is_valid()
        assert "package" in slz.errors
