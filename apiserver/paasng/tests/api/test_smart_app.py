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

"""API Testcases for S-Mart applications"""

import json
import shutil
import tarfile
from pathlib import Path
from typing import Callable, Dict, Optional
from unittest import mock

import pytest
import yaml
from django.conf import settings

from paasng.accessories.publish.market.models import Tag
from paasng.platform.applications.models import Application
from paasng.platform.smart_app.conf import bksmart_settings
from paasng.platform.sourcectl.utils import compress_directory

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SMART_APP_PATH = Path(__file__).resolve().parent / "assets" / "smart_app_v2"


@pytest.fixture(autouse=True)
def _setup_fixtures(mock_wl_services_in_creation):
    """Set fixtures for testings"""
    # Create default tags
    parent_tag = Tag.objects.create(name="demo parent", region=settings.DEFAULT_REGION_NAME)
    Tag.objects.create(name="demo", region=settings.DEFAULT_REGION_NAME, parent=parent_tag)


class TestCreateSMartApp:
    """Test creating S-Mart application"""

    def test_upload_and_create(self, api_client, tmp_path, random_name):
        app_code = f"demo-{random_name}"

        def _desc_updater(desc):
            # Use a random code & name
            desc["app"]["bk_app_code"] = app_code
            desc["app"]["bk_app_name"] = app_code
            return desc

        # API: Upload tarball for creation
        tarball_path = make_smart_tarball(tmp_path, _desc_updater)
        with open(tarball_path, "rb") as file:
            response = api_client.post("/api/sourcectl/smart_packages/", format="multipart", data={"package": file})
        assert response.status_code == 200, f"error: {response.json()['detail']}"
        assert response.json()["app_description"] is not None
        assert response.json()["app_description"]["name"]

        # API: Create application from uploaded tarball
        #
        # In below API call, a ThreadPoolExecutor will be initialized for patching source code
        # concurrently by default. Without real transaction support, the forked worker thread
        # will be unable to retrieve Application object created by main thread because the data
        # was never really committed.
        #
        # Disable parallel processing to let unittest pass.
        with (
            mock.patch("paasng.platform.smart_app.services.dispatch._PARALLEL_PATCHING", new=False),
            mock.patch("moby_distribution.ImageRef.push") as mock_push,
        ):
            mock_push().config.digest.replace.return_value = ""

            response = api_client.post("/api/sourcectl/smart_packages/prepared/")
        assert response.status_code == 201, f"error: {response.json()['detail']}"

        # Verify app info
        app_resp = api_client.get(f"/api/bkapps/applications/{app_code}/")
        assert app_resp.json()["application"]["is_smart_app"] is True


_HEROKU_24_CNB_FILES = {
    ".Version": "cnb-image-layers",
    "artifact.json": json.dumps(
        {"version": "1.0", "runtime": {"base_image_id": "heroku-24", "architecture": "amd64"}}
    ),
}
_DEFAULT_ONLY_IMAGE_CONF = {"default": {"name": "bkpaas/docker/run-heroku-bionic", "tag": "v1.0.0-smart"}}
_HEROKU_24_IMAGE_CONF = {"heroku-24": {"name": "bkpaas/docker/run-heroku-noble", "tag": "v2.5.0-smart"}}


class TestUnsupportedBaseImage:
    """Test uploading S-Mart package whose base image is not configured"""

    @pytest.fixture()
    def app_code(self, random_name):
        return f"demo-{random_name}"

    @pytest.fixture()
    def tarball_path(self, tmp_path, app_code):
        def _desc_updater(desc):
            desc["app"]["bk_app_code"] = app_code
            desc["app"]["bk_app_name"] = app_code
            return desc

        return make_smart_tarball(tmp_path, _desc_updater, extra_files=_HEROKU_24_CNB_FILES)

    def test_reject_on_upload(self, api_client, tarball_path):
        with (
            mock.patch.dict(bksmart_settings.cnb_base_image.image_conf, _DEFAULT_ONLY_IMAGE_CONF, clear=True),
            open(tarball_path, "rb") as file,
        ):
            response = api_client.post("/api/sourcectl/smart_packages/", format="multipart", data={"package": file})
        assert response.status_code == 400
        assert response.json()["code"] == "UNSUPPORTED_SMART_PACKAGE"
        assert "heroku-24" in response.json()["detail"]

    def test_reject_before_creating_app(self, api_client, tarball_path, app_code):
        """暂存后平台不再支持该基础镜像时, 应在创建应用前拒绝, 不能留下未完成的应用"""
        with (
            mock.patch.dict(bksmart_settings.cnb_base_image.image_conf, _HEROKU_24_IMAGE_CONF),
            open(tarball_path, "rb") as file,
        ):
            response = api_client.post("/api/sourcectl/smart_packages/", format="multipart", data={"package": file})
        assert response.status_code == 200, f"error: {response.json()['detail']}"

        with (
            mock.patch.dict(bksmart_settings.cnb_base_image.image_conf, _DEFAULT_ONLY_IMAGE_CONF, clear=True),
            mock.patch("paasng.platform.smart_app.views.dispatch_package_to_modules") as dispatcher,
        ):
            response = api_client.post("/api/sourcectl/smart_packages/prepared/")
        assert response.status_code == 400
        assert response.json()["code"] == "UNSUPPORTED_SMART_PACKAGE"
        assert not dispatcher.called
        assert not Application.objects.filter(code=app_code).exists()


def make_smart_tarball(tmp_path: Path, desc_updater: Callable, extra_files: Optional[Dict[str, str]] = None) -> Path:
    """Make a S-Mart app tarbar file from tempate(located in "./assets")

    :param desc_updater: the function for modifying app desc payload
    :param extra_files: extra files(relative path -> content) to be added to the tarball
    """
    tarball_path = tmp_path / "temp.tar.gz"
    tardir_path = tmp_path / "app"

    # Copy and modify
    shutil.copytree(SMART_APP_PATH, tardir_path)
    with (tardir_path / "app_desc.yaml.tmpl").open(mode="r") as fp:
        desc = yaml.safe_load(fp.read())
        desc["app"]["region"] = settings.DEFAULT_REGION_NAME

        desc = desc_updater(desc)
        (tardir_path / "app_desc.yaml").write_text(yaml.safe_dump(desc))
        (tardir_path / "main").mkdir(exist_ok=True, parents=True)
        with tarfile.open(tardir_path / "main" / "layer.tar.gz", mode="w:gz"):
            pass
        for name, content in (extra_files or {}).items():
            (tardir_path / name).write_text(content)

    compress_directory(tardir_path, tarball_path)
    return tarball_path
