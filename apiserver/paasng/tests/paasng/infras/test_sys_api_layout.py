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

"""Tests for the `sys_api_layout` check."""

from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from rest_framework import viewsets

from paasng.infras.perm_insure import sys_api_layout
from paasng.infras.perm_insure.sys_api_layout import UrlEntry, check_sys_api_view_layout
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class


def make_callback(view_cls):
    """Make a mock callback which carries the given view class."""
    callback = mock.Mock()
    callback.cls = view_cls
    return callback


class SysDemoViewSet(viewsets.ViewSet):
    """A demo view set which follows the conventions."""

    permission_classes = [sysapi_client_perm_class(ClientAction.READ_APPLICATIONS)]


class DemoViewSet(viewsets.ViewSet):
    """A demo view set which serves the user-facing APIs, but mistakenly configures the
    sysapi client permission."""

    permission_classes = [sysapi_client_perm_class(ClientAction.READ_APPLICATIONS)]


class TestCheckSysApiViewLayout:
    """Tests for the `check_sys_api_view_layout` check function."""

    @pytest.fixture()
    def patch_entries(self):
        """Patch the url entries which are inspected by the check function."""

        def _patch(entries: list[UrlEntry]):
            return mock.patch.object(sys_api_layout, "iter_url_patterns", return_value=entries)

        return _patch

    def _make_entries(self, view_cls, *urls, name=None) -> list[UrlEntry]:
        return [UrlEntry(url=url, name=name, callback=make_callback(view_cls)) for url in urls]

    def test_project_passes(self):
        """The project itself should pass the checking, this is the regression guard of the
        conventions described in `sys_api_layout`."""
        assert check_sys_api_view_layout(None) == []

    def test_view_without_sys_prefix(self, patch_entries):
        """E101: the view serves a system API url but its name has no `Sys` prefix."""
        entries = self._make_entries(DemoViewSet, "sys/api/demo/")
        with patch_entries(entries):
            errors = check_sys_api_view_layout(None)

        assert "perm_insure.E101" in {err.id for err in errors}

    def test_sys_view_serves_user_api(self, patch_entries):
        """E101 & E102: the view has the `Sys` prefix and the sysapi client permission, but
        it serves a user-facing url."""
        entries = self._make_entries(SysDemoViewSet, "api/demo/")
        with patch_entries(entries):
            errors = check_sys_api_view_layout(None)

        assert {err.id for err in errors} == {"perm_insure.E101", "perm_insure.E102"}

    def test_sys_view_without_sysapi_perm(self, patch_entries):
        """E102: the view serves a system API url but configures no sysapi client permission."""

        class SysNoPermViewSet(viewsets.ViewSet):
            permission_classes = []

        entries = self._make_entries(SysNoPermViewSet, "sys/api/demo/")
        with patch_entries(entries):
            errors = check_sys_api_view_layout(None)

        assert [err.id for err in errors] == ["perm_insure.E102"]

    def test_url_name_without_sys_prefix(self, patch_entries):
        """E103: the system API url is named without the `sys.` prefix."""
        entries = self._make_entries(SysDemoViewSet, "sys/api/demo/", name="api.demo")
        with patch_entries(entries):
            errors = check_sys_api_view_layout(None)

        assert [err.id for err in errors] == ["perm_insure.E103"]

    def test_user_url_name_with_sys_prefix(self, patch_entries):
        """E103: the user-facing url is named with the `sys.` prefix."""

        class DemoNoPermViewSet(viewsets.ViewSet):
            permission_classes = []

        entries = self._make_entries(DemoNoPermViewSet, "api/demo/", name="sys.demo")
        with patch_entries(entries):
            errors = check_sys_api_view_layout(None)

        assert [err.id for err in errors] == ["perm_insure.E103"]

    def test_module_defines_both_views(self, patch_entries):
        """E104: a module defines both the `Sys` and non-`Sys` view classes, the two classes
        are defined in the same module (this test module)."""
        entries = self._make_entries(SysDemoViewSet, "sys/api/demo/") + self._make_entries(
            DemoViewSet, "sys/api/demo/"
        )
        with patch_entries(entries):
            errors = check_sys_api_view_layout(None)

        assert "perm_insure.E104" in {err.id for err in errors}

    def test_violation_blocks_startup(self):
        """A violation should be registered to the Django check framework and block the
        startup of the project."""

        def _fake_entries():
            yield UrlEntry(url="sys/api/demo/", name="api.demo", callback=make_callback(DemoViewSet))

        with (
            mock.patch.object(sys_api_layout, "iter_url_patterns", _fake_entries),
            pytest.raises(SystemCheckError, match=r"(?s).*perm_insure\.E10.*"),
        ):
            call_command("check")
