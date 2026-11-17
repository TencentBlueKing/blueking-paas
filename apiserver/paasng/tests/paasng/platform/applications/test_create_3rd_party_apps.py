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

from pathlib import Path
from typing import List
from unittest import mock

import pytest
import yaml
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import override_settings

from paasng.infras.bk_user.entities import VirtualUser
from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.members.models import ApplicationGradeManager
from paasng.platform.applications.management.commands.create_3rd_party_apps import BuiltinAdminResolver
from paasng.platform.applications.models import Application
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db

CMD_MODULE = "paasng.platform.applications.management.commands.create_3rd_party_apps"


@pytest.fixture()
def app_code() -> str:
    return "ut" + generate_random_string(length=10).lower()


@pytest.fixture()
def source_file(tmp_path: Path, app_code: str) -> str:
    """只包含一个第三方应用的描述文件"""
    path = tmp_path / "3rd_apps.yaml"
    path.write_text(
        yaml.safe_dump(
            [
                {
                    "code": app_code,
                    "name": app_code,
                    "name_en": app_code,
                    "tag": "",
                    "logo": "",
                    "introduction_zh_cn": "",
                    "introduction_en": "",
                    "source_tp_url": "http://example.com",
                }
            ]
        )
    )
    return str(path)


class TestCreate3rdPartyApps:
    def test_rollback_when_iam_init_failed(self, source_file: str, app_code: str):
        """权限中心初始化失败时，不应在本地残留应用及分级管理员记录"""

        def _register_then_fail(application: Application, add_creator_to_admin_group: bool = True):
            # 第三方应用创建时不应把创建者加入管理者用户组
            assert add_creator_to_admin_group is False
            ApplicationGradeManager.objects.create(
                app_code=application.code, grade_manager_id=1, tenant_id=application.tenant_id
            )
            raise BKIAMGatewayServiceError("iam model not found")

        with (
            mock.patch(f"{CMD_MODULE}.AppManger") as mocked_app_manager,
            mock.patch(
                f"{CMD_MODULE}.register_builtin_user_groups_and_grade_manager", side_effect=_register_then_fail
            ),
        ):
            mocked_app_manager.return_value.get.return_value = None
            call_command("create_3rd_party_apps", "--source", source_file, "--app_codes", app_code, "--override=true")

        assert not Application.objects.filter(code=app_code).exists()
        assert not ApplicationGradeManager.objects.filter(app_code=app_code).exists()

    @pytest.mark.parametrize(
        ("yaml_creator", "expected_creator"),
        [
            # 未指定 creator 时使用平台内置管理员
            (None, user_id_encoder.encode(settings.USER_TYPE, "bk_admin_x7k2p")),
            # 指定了 creator 时原样使用
            ("0335cce79c92", "0335cce79c92"),
        ],
    )
    def test_creator(self, tmp_path: Path, app_code: str, yaml_creator, expected_creator):
        app_desc = {
            "code": app_code,
            "name": app_code,
            "name_en": app_code,
            "tag": "",
            "logo": "",
            "introduction_zh_cn": "",
            "introduction_en": "",
            "source_tp_url": "http://example.com",
        }
        if yaml_creator:
            app_desc["creator"] = yaml_creator
        path = tmp_path / "3rd_apps.yaml"
        path.write_text(yaml.safe_dump([app_desc]))

        with (
            override_settings(ENABLE_MULTI_TENANT_MODE=False, ADMIN_USERNAME="bk_admin_x7k2p"),
            mock.patch(f"{CMD_MODULE}.AppManger") as mocked_app_manager,
            mock.patch(f"{CMD_MODULE}.Command.create_3rd_app") as mocked_create,
        ):
            mocked_app_manager.return_value.get.return_value = None
            call_command("create_3rd_party_apps", "--source", str(path), "--app_codes", app_code, "--override=true")

        assert mocked_create.call_args.args[0].creator == expected_creator


class TestBuiltinAdminResolver:
    def test_single_tenant(self):
        with override_settings(ENABLE_MULTI_TENANT_MODE=False, ADMIN_USERNAME="admin"):
            # 与 Chart 中 3rd_apps.yaml 写死的 creator 一致
            assert BuiltinAdminResolver().get_user_id("default") == "0335cce79c92"

    def test_multi_tenant(self):
        def _lookup(login_names: List[str]) -> List[VirtualUser]:
            assert login_names == ["bk_admin_x7k2p"]
            return [VirtualUser(bk_username="gtrydp5fs282bptk", login_name="bk_admin_x7k2p")]

        with (
            override_settings(ENABLE_MULTI_TENANT_MODE=True, ADMIN_USERNAME="bk_admin_x7k2p"),
            mock.patch(f"{CMD_MODULE}.BkUserClient") as mocked_client,
        ):
            mocked_client.return_value.batch_lookup_virtual_users_by_login_name.side_effect = _lookup
            resolver = BuiltinAdminResolver()
            user_id = resolver.get_user_id("system")
            # 同一租户只查询一次
            assert resolver.get_user_id("system") == user_id

        assert user_id == user_id_encoder.encode(settings.USER_TYPE, "gtrydp5fs282bptk")
        mocked_client.assert_called_once_with("system")

    def test_multi_tenant_not_found(self):
        with (
            override_settings(ENABLE_MULTI_TENANT_MODE=True, ADMIN_USERNAME="bk_admin_x7k2p"),
            mock.patch(f"{CMD_MODULE}.BkUserClient") as mocked_client,
        ):
            mocked_client.return_value.batch_lookup_virtual_users_by_login_name.return_value = []
            with pytest.raises(CommandError):
                BuiltinAdminResolver().get_user_id("system")
