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

"""Tests for serializers module"""

import pytest

from paasng.platform.sourcectl.serializers import SourcePackageUploadViaUrlSLZ


def _make_data(package_url: str) -> dict:
    return {"package_url": package_url, "version": "1.0.0", "allow_overwrite": False}


class TestSourcePackageUploadViaUrlSLZ:
    """Tests for SourcePackageUploadViaUrlSLZ serializer"""

    def test_empty_whitelist_rejects(self, settings):
        settings.SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS = []
        slz = SourcePackageUploadViaUrlSLZ(data=_make_data("https://example.com/pkg.tar.gz"))

        assert not slz.is_valid()
        assert "package_url" in slz.errors

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/path/to/pkg.tar.gz",
            "http://example.com/pkg.tar.gz",
            "https://example.com:443/pkg.tar.gz",
            "http://example.com:80/pkg.tar.gz",
        ],
        ids=["https-default", "http-default", "https-explicit-443", "http-explicit-80"],
    )
    def test_whitelisted_host_standard_port_passes(self, settings, url):
        settings.SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS = ["example.com"]
        slz = SourcePackageUploadViaUrlSLZ(data=_make_data(url))
        assert slz.is_valid(), slz.errors

    def test_multiple_allowed_hosts(self, settings):
        settings.SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS = ["cdn1.example.com", "cdn2.example.com"]
        for host in ("cdn1.example.com", "cdn2.example.com"):
            slz = SourcePackageUploadViaUrlSLZ(data=_make_data(f"https://{host}/pkg.tar.gz"))
            assert slz.is_valid(), slz.errors

    def test_host_matching_is_case_insensitive(self, settings):
        settings.SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS = ["Example.COM"]
        slz = SourcePackageUploadViaUrlSLZ(data=_make_data("https://example.com/pkg.tar.gz"))
        assert slz.is_valid(), slz.errors

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil.com/pkg.tar.gz",
            "http://192.168.1.1/pkg.tar.gz",
            "http://10.0.0.1/pkg.tar.gz",
            "http://127.0.0.1/pkg.tar.gz",
            "http://localhost/pkg.tar.gz",
        ],
        ids=["unknown-host", "private-192", "private-10", "loopback", "localhost"],
    )
    def test_non_whitelisted_host_rejected(self, settings, url):
        settings.SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS = ["allowed.example.com"]
        slz = SourcePackageUploadViaUrlSLZ(data=_make_data(url))
        assert not slz.is_valid()
        assert "package_url" in slz.errors

    @pytest.mark.parametrize(
        "port",
        [8080, 8443, 22],
        ids=["8080", "8443", "ssh-22"],
    )
    def test_nonstandard_port_rejected(self, settings, port):
        settings.SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS = ["example.com"]
        slz = SourcePackageUploadViaUrlSLZ(data=_make_data(f"https://example.com:{port}/pkg.tar.gz"))
        assert not slz.is_valid()
        assert "package_url" in slz.errors

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/pkg.tar.gz",
            "file:///etc/passwd",
            "gopher://example.com/file",
        ],
        ids=["ftp", "file", "gopher"],
    )
    def test_disallowed_scheme_rejected(self, settings, url):
        settings.SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS = ["example.com"]
        slz = SourcePackageUploadViaUrlSLZ(data=_make_data(url))
        assert not slz.is_valid()
        assert "package_url" in slz.errors
