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

import string
from pathlib import Path
from unittest import mock

import pytest
import yaml
from django.conf import settings

from paasng.platform.applications.constants import ApplicationType
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


@pytest.fixture()
def lesscode_public_params():
    return {
        "type": "default",
        "engine_enabled": True,
        "engine_params": {"source_init_template": settings.DUMMY_TEMPLATE_NAME},
    }


class TestApiInAPIGW:
    """Test APIs registered on APIGW, the input and output parameters of these APIs cannot be changed at will"""

    @pytest.mark.usefixtures("_init_tmpls")
    def test_create_lesscode_api(self, bk_user, api_client, lesscode_public_params, bk_app_code, bk_app_name):
        lesscode_public_params.update(
            {
                "region": settings.DEFAULT_REGION_NAME,
                "code": bk_app_code,
                "name": bk_app_name,
            }
        )
        response = api_client.post("/apigw/api/bkapps/applications/", data=lesscode_public_params)
        assert response.status_code == 201
        assert response.json()["application"]["modules"][0]["source_origin"] == SourceOrigin.BK_LESS_CODE
        assert response.json()["application"]["type"] == ApplicationType.CLOUD_NATIVE


class TestModuleSourcePackageViewSet:
    """测试源码包上传的接口"""

    @pytest.fixture()
    def contents(self):
        """The default contents for making tar file."""
        app_desc = {
            "spec_version": 2,
            "module": {"is_default": True, "processes": {"web": {"command": "npm run online"}}, "language": "NodeJS"},
        }
        return {"app_desc.yaml": yaml.safe_dump(app_desc)}

    @pytest.fixture()
    def tar_path(self, contents):
        with generate_temp_file() as file_path:
            gen_tar(file_path, contents)
            yield file_path

    def test_upload_with_app_desc(self, api_client, bk_app, bk_module, tar_path):
        bk_module.source_origin = SourceOrigin.BK_LESS_CODE
        bk_module.save()
        url = "/api/bkapps/applications/{code}/modules/{module_name}/source_package/link/".format(
            code=bk_app.code, module_name=bk_module.name
        )

        def download_file_via_url(url, local_path: Path):
            local_path.write_bytes(tar_path.read_bytes())

        with mock.patch(
            "paasng.platform.sourcectl.package.uploader.download_file_via_url",
            side_effect=download_file_via_url,
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
