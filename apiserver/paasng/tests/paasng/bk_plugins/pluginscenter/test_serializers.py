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

from typing import Dict
from unittest import mock

import cattr
import pytest
from blue_krill.web.std_error import APIError
from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework.exceptions import ErrorDetail

from paasng.bk_plugins.pluginscenter import serializers
from paasng.bk_plugins.pluginscenter.constants import PluginRevisionType
from paasng.bk_plugins.pluginscenter.definitions import PluginCodeTemplate
from paasng.core.tenant.constants import AppTenantMode
from paasng.utils.i18n import to_translated_field

pytestmark = pytest.mark.django_db


def make_translate_fields(field, value) -> Dict:
    return {to_translated_field(field, language_code=language[0]): value for language in settings.LANGUAGES}


@pytest.fixture()
def mocked_plugin_repo_accessor():
    with mock.patch("paasng.bk_plugins.pluginscenter.shim.get_plugin_repo_accessor") as mocked:
        yield mocked


@pytest.mark.parametrize(
    ("data", "is_valid", "expected"),
    [
        (
            {"id": 1, "name": "2", "template": "foo"},
            True,
            {
                "id": "1",
                **make_translate_fields("name", "2"),
                "template": cattr.structure(
                    {
                        "id": "foo",
                        "name": "Foo Template",
                        "language": "Python",
                        "repository": "https://example.com/foo",
                    },
                    PluginCodeTemplate,
                ),
                "extra_fields": {},
                "plugin_tenant_mode": AppTenantMode.GLOBAL,
            },
        ),
        (
            {"id": "12345678901", "name": "2", "template": "foo"},
            False,
            {"id": [ErrorDetail(string="请确保这个字段不能超过 10 个字符。", code="max_length")]},
        ),
        (
            {
                "id": 1,
                "name": "2",
                "template": "foo",
                "extra_fields": {"email": "foo@example.com", "distributor_codes": ["1", "2"]},
            },
            True,
            {
                "id": "1",
                **make_translate_fields("name", "2"),
                "template": cattr.structure(
                    {
                        "id": "foo",
                        "name": "Foo Template",
                        "language": "Python",
                        "repository": "https://example.com/foo",
                    },
                    PluginCodeTemplate,
                ),
                "extra_fields": {"email": "foo@example.com", "distributor_codes": ["1", "2"]},
                "plugin_tenant_mode": AppTenantMode.GLOBAL,
            },
        ),
        (
            {"id": "invalid_id", "name": "2", "template": "foo"},
            False,
            {"id": [ErrorDetail(string=_("This value does not match the required pattern."), code="invalid")]},
        ),
        (
            {
                "id": "1",
                "name": "2",
                "template": "foo",
                "extra_fields": {"email": "invalid.email", "distributor_codes": []},
            },
            False,
            {
                "extra_fields": {
                    "email": [ErrorDetail(string=_("This value does not match the required pattern."), code="invalid")]
                }
            },
        ),
    ],
)
def test_make_create_plugin_validator(pd, data, is_valid, expected, mocked_plugin_repo_accessor):
    slz = serializers.make_plugin_slz_class(pd, creation=True)(data=data, context={"pd": pd})
    if is_valid:
        slz.is_valid(raise_exception=True)
        assert expected == slz.validated_data
    else:
        assert not slz.is_valid()
        assert slz.errors == expected


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("id", 1, {"non_field_errors": [ErrorDetail(string="插件ID 为 1 的插件已存在", code="unique")]}),
        (
            "name_en",
            "FLAG",
            {"non_field_errors": [ErrorDetail(string="插件名称 为 FLAG 的插件已存在", code="unique")]},
        ),
        (
            "name_zh_cn",
            "FLAG",
            {"non_field_errors": [ErrorDetail(string="插件名称 为 FLAG 的插件已存在", code="unique")]},
        ),
    ],
)
def test_make_create_plugin_validator_conflict(pd, plugin, field, value, expected):
    setattr(plugin, field, value)
    plugin.save()
    data = {
        "id": 1,
        "name_en": "FLAG",
        "name_zh_cn": "FLAG",
        "name": "FLAG",
        "template": plugin.template.name,
        "extra_fields": {"email": "foo@example.com", "distributor_codes": []},
    }
    slz = serializers.make_plugin_slz_class(pd, creation=True)(data=data, context={"pd": pd})
    assert not slz.is_valid()
    assert slz.errors == expected


COMMON_DATA = {"source_version_name": "...", "source_version_type": "...", "comment": "..."}


@pytest.mark.parametrize(
    ("previous_version", "data", "is_valid"),
    [
        ("0.1.2", {"semver_type": "major", "version": "1.0.0", **COMMON_DATA}, True),
        ("0.1.2", {"semver_type": "minor", "version": "0.2.0", **COMMON_DATA}, True),
        ("0.1.2", {"semver_type": "patch", "version": "0.1.3", **COMMON_DATA}, True),
        ("0.1.2", {"semver_type": "patch", "version": "0.2.2", **COMMON_DATA}, False),
        ("0.1.2", {"semver_type": "patch", "version": "0.1.3.4", **COMMON_DATA}, False),
    ],
)
def test_validate_automatic_semver(plugin, previous_version, data, is_valid, mocked_plugin_repo_accessor):
    plugin.pd.release_revision.versionNo = "automatic"
    slz = serializers.make_create_release_version_slz_class(plugin, "prod")(
        data=data, context={"previous_version": previous_version}
    )
    if is_valid:
        slz.is_valid(raise_exception=True)
    else:
        assert not slz.is_valid()


@pytest.mark.parametrize(
    ("data", "is_valid"),
    [
        ({"version": "1.0.0", **COMMON_DATA, "source_version_name": "1.0.0"}, True),
        ({"version": "1.0.0", **COMMON_DATA, "source_version_name": "2.0.0"}, False),
    ],
)
def test_validate_revision_eq_source_revision(plugin, data, is_valid, mocked_plugin_repo_accessor):
    plugin.pd.release_revision.versionNo = "revision"
    slz = serializers.make_create_release_version_slz_class(plugin, "prod")(data=data)
    if is_valid:
        slz.is_valid(raise_exception=True)
    else:
        assert not slz.is_valid()


@pytest.mark.parametrize(
    ("source_hash", "data", "is_valid"),
    [
        (
            "a407e44060597e4030d1872d1588c279686e90cb",
            {"version": "a407e44060597e4030d1872d1588c279686e90cb", **COMMON_DATA},
            True,
        ),
        (
            "46d1c7f757b690b741a01b8d677c2f9ce931b6a1",
            {"version": "1.0.0", **COMMON_DATA},
            False,
        ),
    ],
)
def test_validate_revision_eq_commit_hash(plugin, source_hash, data, is_valid, mocked_plugin_repo_accessor):
    plugin.pd.release_revision.versionNo = "commit-hash"
    mocked_plugin_repo_accessor().extract_smart_revision.return_value = source_hash
    slz = serializers.make_create_release_version_slz_class(plugin, "prod")(data=data)
    if is_valid:
        slz.is_valid(raise_exception=True)
    else:
        assert not slz.is_valid()


@pytest.mark.parametrize(
    ("data", "is_valid"),
    [
        ({"release_id": "1", "version": "1.0.0", **COMMON_DATA, "source_version_name": "1.0.0"}, True),
        ({"release_id": "", "version": "1.0.0", **COMMON_DATA, "source_version_name": "1.0.0"}, False),
        ({"version": "1.0.0", **COMMON_DATA, "source_version_name": "2.0.0"}, False),
    ],
)
def test_validate_tested_version(plugin, data, is_valid):
    plugin.pd.release_revision.revisionType = PluginRevisionType.TESTED_VERSION
    plugin.pd.release_revision.versionNo = "revision"

    with mock.patch(
        "paasng.bk_plugins.pluginscenter.serializers.get_source_hash_by_plugin_version", return_value="hash"
    ):
        slz = serializers.make_create_release_version_slz_class(plugin, "prod")(data=data)
        if is_valid:
            slz.is_valid(raise_exception=True)
        else:
            assert not slz.is_valid()


@pytest.mark.parametrize(
    ("data", "revision_policy", "is_valid"),
    [
        ({"version": "1.0.0", **COMMON_DATA, "source_version_name": "master"}, None, True),
        (
            {"version": "1.0.0", **COMMON_DATA, "source_version_name": "master"},
            "disallow_released_source_version",
            False,
        ),
        (
            {"version": "1.0.0", **COMMON_DATA, "source_version_name": "master"},
            "disallow_releasing_source_version",
            False,
        ),
    ],
)
def test_validate_release_policy(plugin, release, data, revision_policy, is_valid, mocked_plugin_repo_accessor):
    plugin.pd.release_revision.versionNo = "self-fill"
    plugin.pd.release_revision.revisionPolicy = revision_policy
    slz = serializers.make_create_release_version_slz_class(plugin, "prod")(data=data)
    if is_valid:
        slz.is_valid(raise_exception=True)
    else:
        with pytest.raises(APIError):
            slz.is_valid(raise_exception=True)


@pytest.mark.parametrize(
    ("data", "is_valid"),
    [
        ({"category": "1", "introduction": "2", "description": "3", "contact": "4"}, True),
        ({"category": "1", "introduction_zh_cn": "2", "description": "3", "contact": "4"}, False),
        ({"category": "1", "introduction_en": "2", "description": "3", "contact": "4"}, False),
        (
            {
                "category": "1",
                "introduction_zh_cn": "2",
                "introduction_en": "2",
                "description": "3",
                "contact": "4",
            },
            True,
        ),
    ],
)
def test_market_info_validator(pd, data, is_valid):
    slz = serializers.make_market_info_slz_class(pd)(data=data)
    if is_valid:
        slz.is_valid(raise_exception=True)
    else:
        assert not slz.is_valid()
