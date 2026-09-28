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
from unittest import mock

import pytest
import yaml
from django.core.management import call_command

from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.members.models import ApplicationGradeManager
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

        def _register_then_fail(application: Application):
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
