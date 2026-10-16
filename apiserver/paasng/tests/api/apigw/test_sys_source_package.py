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
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from rest_framework import status

from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.models import SourcePackage
from paasng.platform.sourcectl.utils import generate_temp_file
from tests.paasng.platform.sourcectl.packages.utils import gen_tar
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _sys_upload_url(app_code: str, module_name: str) -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/source_package/link/"


@pytest.fixture()
def tar_path():
    app_desc = {
        "spec_version": 2,
        "module": {
            "is_default": True,
            "processes": {"web": {"command": "gunicorn bk_plugin_runtime.wsgi --timeout 120 -k gevent -w 2"}},
            "language": "python",
        },
    }
    contents = {"app_desc.yml": yaml.safe_dump(app_desc)}

    with generate_temp_file() as file_path:
        gen_tar(file_path, contents)
        yield file_path


@pytest.fixture()
def patch_download(tar_path):
    """Stub out the remote download, the tar file is served from the local disk instead."""

    def download_file_via_url(url, local_path: Path):
        local_path.write_bytes(tar_path.read_bytes())

    with mock.patch(
        "paasng.platform.sourcectl.package.uploader.download_file_via_url",
        side_effect=download_file_via_url,
    ):
        yield


@pytest.fixture()
def ai_agent_module(bk_module):
    """An AI Agent module which can be deployed via source package."""
    bk_module.application.is_ai_agent_app = True
    bk_module.application.save(update_fields=["is_ai_agent_app"])
    bk_module.source_origin = SourceOrigin.AI_AGENT
    bk_module.save(update_fields=["source_origin"])
    return bk_module


class TestSysUploadSourcePackageViaLink:
    """应用态上传源码包接口 upload_source_package_via_link 测试"""

    @pytest.fixture(autouse=True)
    def _allow_upload_host(self, settings):
        # Set the allowed hosts otherwise the URL validation will fail
        settings.SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS = ["example.com"]

    def test_upload_success(self, sys_aidev_api_client, ai_agent_module, patch_download):
        """AIDEV 可以用应用态凭证为 AI Agent 应用上传源码包。"""
        operator = create_user()
        resp = sys_aidev_api_client.post(
            _sys_upload_url(ai_agent_module.application.code, ai_agent_module.name),
            data={
                "package_url": "https://example.com/pkg.tar.gz",
                "version": "0.0.1",
                "allow_overwrite": True,
                "operator": operator.username,
            },
        )

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        body = resp.json()
        assert body["version"] == "0.0.1"
        assert body["operator"] == operator.username

        # 源码包的 owner 应为请求体中的 operator，而不是匿名用户
        package = SourcePackage.objects.get(module=ai_agent_module, version="0.0.1")
        assert package.owner == user_id_encoder.encode(settings.USER_TYPE, operator.username)

    @pytest.mark.parametrize("client_fixture", ["sys_api_client", "sys_lesscode_api_client"])
    def test_non_aidev_client_denied(
        self,
        client_fixture: str,
        request: pytest.FixtureRequest,
        ai_agent_module,
        patch_download,
    ):
        """非 AIDEV 调用方（含 BASIC_MAINTAINER / LESSCODE）返回 403。"""
        client = request.getfixturevalue(client_fixture)
        operator = create_user()
        resp = client.post(
            _sys_upload_url(ai_agent_module.application.code, ai_agent_module.name),
            data={
                "package_url": "https://example.com/pkg.tar.gz",
                "version": "0.0.1",
                "allow_overwrite": True,
                "operator": operator.username,
            },
        )

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"
        assert not SourcePackage.objects.filter(module=ai_agent_module, version="0.0.1").exists()

    def test_non_ai_agent_app_denied(self, sys_aidev_api_client, bk_app, bk_module, patch_download):
        """对非 AI Agent 应用调用时返回 403。"""
        assert bk_app.is_ai_agent_app is False
        operator = create_user()

        resp = sys_aidev_api_client.post(
            _sys_upload_url(bk_app.code, bk_module.name),
            data={
                "package_url": "https://example.com/pkg.tar.gz",
                "version": "0.0.1",
                "allow_overwrite": True,
                "operator": operator.username,
            },
        )

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"
        assert not SourcePackage.objects.filter(module=bk_module, version="0.0.1").exists()

    def test_non_ai_agent_module_denied(self, sys_aidev_api_client, ai_agent_module, patch_download):
        """AI Agent 应用下不支持包部署的模块（如 git 部署）返回 400。"""
        ai_agent_module.source_origin = SourceOrigin.AUTHORIZED_VCS
        ai_agent_module.save(update_fields=["source_origin"])
        operator = create_user()

        resp = sys_aidev_api_client.post(
            _sys_upload_url(ai_agent_module.application.code, ai_agent_module.name),
            data={
                "package_url": "https://example.com/pkg.tar.gz",
                "version": "0.0.1",
                "allow_overwrite": True,
                "operator": operator.username,
            },
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "UNSUPPORTED_SOURCE_ORIGIN"
