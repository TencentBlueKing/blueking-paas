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

from paasng.infras.accounts.permissions.global_site import global_site_resource
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.service_proxy.plugins import (
    ApplicationInPathExtractor,
    ExtractedAppBasicInfo,
    get_current_instances,
    list_site_permissions,
)
from tests.utils import mock

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _patch_list_app_perms():
    with mock.patch(
        "paasng.misc.service_proxy.plugins.list_application_permissions",
        return_value={action: True for action in AppAction},
    ):
        yield


def test_get_current_instances(bk_user, bk_app):
    insts = get_current_instances(bk_user, f"applications/{bk_app.code}/modules/default/envs/stag/")
    assert insts[0]["type"] == "application"
    assert isinstance(insts[0]["value"], dict)
    assert isinstance(insts[0]["perms_map"], dict)

    assert insts[1]["type"] == "global_site"
    assert isinstance(insts[1]["value"], str)
    assert isinstance(insts[1]["perms_map"], dict)


@pytest.fixture()
def site_permissions(bk_user):
    role = global_site_resource.get_role_of_user(bk_user, None)
    result = {}
    for name, _ in global_site_resource.permissions:
        result[name] = role.has_perm(name)
    return result


def test_get_current_instances_none(bk_user, site_permissions):
    insts = get_current_instances(bk_user, "/foo/bar")
    assert insts == [{"type": "global_site", "value": "user", "perms_map": site_permissions}]


class TestApplicationInPathExtractor:
    @pytest.mark.parametrize(
        ("request_path", "expected_result"),
        [
            ("foo/bar", None),
            (
                "applications/foo/",
                ExtractedAppBasicInfo(code="foo"),
            ),
            (
                "applications/foo/modules/bar/",
                ExtractedAppBasicInfo(code="foo", module_name="bar"),
            ),
            (
                "applications/foo/envs/stag/",
                ExtractedAppBasicInfo(code="foo", module_name=None, environment="stag"),
            ),
            (
                "applications/foo/modules/bar/envs/stag/",
                ExtractedAppBasicInfo(code="foo", module_name="bar", environment="stag"),
            ),
        ],
    )
    def test_extract_basic(self, request_path, expected_result):
        ret = ApplicationInPathExtractor().extract_basic(request_path)
        assert ret == expected_result

    def test_extract_objects(self, bk_app):
        request_path = f"applications/{bk_app.code}/modules/default/envs/stag/"
        ret = ApplicationInPathExtractor().extract_objects(request_path)
        assert ret is not None
        assert ret.application is not None
        assert ret.application.code == bk_app.code
        assert ret.module is not None
        assert ret.module.name == "default"
        assert ret.module_env is not None
        assert ret.module_env.environment == "stag"
        assert ret.engine_app is not None
        assert ret.engine_app.name is not None


def test_list_site_permissions(bk_user, site_permissions):
    permissions = list_site_permissions(bk_user)
    assert permissions == site_permissions
