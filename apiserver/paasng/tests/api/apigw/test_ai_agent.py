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

import string
from pathlib import Path
from unittest import mock

import pytest
import yaml
from django.conf import settings

from paasng.platform.applications.constants import ApplicationType, DeployPolicy
from paasng.platform.applications.models import Application
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.utils import generate_temp_file
from tests.paasng.platform.sourcectl.packages.utils import gen_tar
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def bk_app_code():
    return generate_random_string(8, string.ascii_lowercase)


@pytest.fixture()
def bk_app_name():
    return generate_random_string(8)


class TestAIAgentViewSet:
    """AI Agent 插件创建、上传源码包接口测试"""

    @pytest.fixture()
    def contents(self):
        """The default contents for making tar file."""

        # 目前插件应用的模板都是使用 spec_version=2 的应用描述文件
        app_desc = {
            "spec_version": 2,
            "module": {
                "is_default": True,
                "processes": {
                    "web": {
                        "command": "gunicorn bk_plugin_runtime.wsgi --timeout 120 -k gevent -w 2 --max-requests=1000"
                    }
                },
                "language": "python",
            },
        }
        return {"app_desc.yml": yaml.safe_dump(app_desc)}

    @pytest.fixture()
    def tar_path(self, contents):
        with generate_temp_file() as file_path:
            gen_tar(file_path, contents)
            yield file_path

    @pytest.mark.usefixtures("_init_tmpls")
    def test_create_ai_agent_app(
        self,
        bk_user,
        api_client,
        mock_wl_services_in_creation,
        bk_app_code,
        bk_app_name,
    ):
        params = {
            "region": settings.DEFAULT_REGION_NAME,
            "code": bk_app_code,
            "name": bk_app_name,
        }
        response = api_client.post(
            "/api/bkapps/ai_agent/",
            data=params,
        )
        assert response.status_code == 201
        assert response.json()["application"]["modules"][0]["source_origin"] == SourceOrigin.AI_AGENT
        assert response.json()["application"]["type"] == ApplicationType.CLOUD_NATIVE
        assert response.json()["application"]["is_ai_agent_app"] is True
        assert response.json()["application"]["is_plugin_app"] is True

    @pytest.mark.usefixtures("_init_tmpls")
    @pytest.mark.usefixtures("mock_initialize_vcs_with_template")
    @pytest.mark.parametrize(
        ("build_method", "extra_build_config", "is_isolated"),
        [
            # 使用 git 仓库 + dockerfile 构建
            ("dockerfile", {"dockerfile_path": "Dockerfile"}, False),
            # 使用 git 仓库 + buildpack 构建
            ("buildpack", {}, False),
            # 使用 git 仓库 + dockerfile 构建，标记为隔离部署
            ("dockerfile", {"dockerfile_path": "Dockerfile"}, True),
        ],
    )
    def test_create_ai_agent_app_via_git(
        self,
        bk_user,
        api_client,
        mock_wl_services_in_creation,
        bk_app_code,
        bk_app_name,
        build_method,
        extra_build_config,
        is_isolated,
    ):
        """传入 source_config 时，AI Agent 应用走 git 仓库部署（支持 buildpack / dockerfile）"""
        response = api_client.post(
            "/api/bkapps/ai_agent/",
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "is_isolated": is_isolated,
                "bkapp_spec": {"build_config": {"build_method": build_method, **extra_build_config}},
                "source_config": {
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert response.status_code == 201, f"error: {response.json()['detail']}"
        app_data = response.json()["application"]
        assert app_data["type"] == ApplicationType.CLOUD_NATIVE
        assert app_data["is_ai_agent_app"] is True
        assert app_data["is_plugin_app"] is True
        assert app_data["modules"][0]["web_config"]["build_method"] == build_method

        # 校验隔离部署标记正确落库（对外 is_isolated 布尔映射为 deploy_policy 枚举）
        application = Application.objects.get(code=bk_app_code)
        assert application.is_ai_agent_app is True
        expected_policy = DeployPolicy.ISOLATED.value if is_isolated else DeployPolicy.DEFAULT.value
        assert application.deploy_policy == expected_policy

    def test_create_ai_agent_app_via_git_without_bkapp_spec(self, api_client, bk_app_code, bk_app_name):
        """传入 source_config 但缺少 bkapp_spec 时，应校验失败"""
        response = api_client.post(
            "/api/bkapps/ai_agent/",
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "source_config": {
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert response.status_code == 400
        assert response.json()["code"] == "VALIDATION_ERROR"

    def test_create_engineless_ai_agent_app(
        self,
        bk_user,
        api_client,
        bk_app_code,
        bk_app_name,
    ):
        """创建 engineless AI Agent 外链应用：type=engineless_app, is_plugin_app=False"""
        response = api_client.post(
            "/api/bkapps/ai_agent/",
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "is_engineless": True,
            },
        )
        assert response.status_code == 201, f"error: {response.json()}"
        app_data = response.json()["application"]
        assert app_data["type"] == ApplicationType.ENGINELESS_APP
        assert app_data["is_ai_agent_app"] is True
        # 占位外链应用不是插件，不应注册网关
        assert app_data["is_plugin_app"] is False

    def test_engineless_ai_agent_hidden_from_user_list(
        self,
        api_client,
        bk_app,
        bk_app_code,
        bk_app_name,
    ):
        """创建 engineless AI Agent 应用后, 不应出现在用户应用列表中"""
        # 先建一个 engineless AI Agent 应用
        resp = api_client.post(
            "/api/bkapps/ai_agent/",
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "is_engineless": True,
            },
        )
        assert resp.status_code == 201

        # 查询用户应用列表, 验证 engineless AI Agent 不可见
        with mock.patch("paasng.platform.applications.views.application.get_exposed_links", return_value={}):
            list_resp = api_client.get("/api/bkapps/applications/lists/detailed")

        assert list_resp.status_code == 200
        app_codes = {item["application"]["code"] for item in list_resp.json()["results"]}

        # engineless AI Agent 应用不应出现在列表中
        assert bk_app_code not in app_codes
        # 常规应用应该在列表中 (确保测试有意义)
        assert bk_app.code in app_codes

    def test_upload_with_app_desc(self, api_client, bk_app, bk_module, tar_path, settings):
        # Set the allowed hosts otherwise the validation will fail
        settings.SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS = ["example.com"]

        bk_module.source_origin = SourceOrigin.AI_AGENT
        bk_module.save()
        url = "/api/bkapps/applications/{code}/modules/{module_name}/source_package/link/".format(
            code=bk_app.code, module_name=bk_module.name
        )

        def download_file_via_url(url, local_path: Path):
            local_path.write_bytes(tar_path.read_bytes())

        with mock.patch(
            "paasng.platform.sourcectl.package.uploader.download_file_via_url", side_effect=download_file_via_url
        ):
            response = api_client.post(
                url,
                data={
                    "package_url": "https://example.com",
                    "version": "0.0.1",
                    "allow_overwrite": True,
                },
            )

        assert response.status_code == 200
