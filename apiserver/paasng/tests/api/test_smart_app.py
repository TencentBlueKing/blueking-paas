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

import shutil
import tarfile
from pathlib import Path
from typing import Callable
from unittest import mock

import pytest
import yaml
from django.conf import settings
from django.urls import reverse

from paasng.accessories.publish.market.models import MarketConfig, Tag
from paasng.platform.applications.models import Application, SMartAppExtraInfo
from paasng.platform.sourcectl.utils import compress_directory

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SMART_APP_V2_PATH = Path(__file__).resolve().parent / "assets" / "smart_app_v2"
SMART_APP_V3_PATH = Path(__file__).resolve().parent / "assets" / "smart_app_v3"


@pytest.fixture(autouse=True)
def _setup_fixtures(mock_wl_services_in_creation):
    """Set fixtures for testings"""
    # Create default tags
    parent_tag = Tag.objects.create(name="demo parent")
    Tag.objects.create(name="demo", parent=parent_tag)


@pytest.fixture(autouse=True)
def _mock_dispatch_smart_app():
    """mock dispatch smart app"""

    # A ThreadPoolExecutor will be initialized for patching source code
    # concurrently by default. Without real transaction support, the forked worker thread
    # will be unable to retrieve Application object created by main thread because the data
    # was never really committed.
    #
    # Disable parallel processing to let unittest pass.

    with (
        mock.patch("paasng.platform.smart_app.services.dispatch._PARALLEL_PATCHING", new=False),
        mock.patch("paasng.utils.moby_distribution.ImageRef.push") as mock_push,
    ):
        mock_push().config.digest.replace.return_value = ""
        yield


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
        tarball_path = make_smart_tarball(tmp_path, _desc_updater, version="v2")
        with open(tarball_path, "rb") as file:
            response = api_client.post("/api/bkapps/s-mart/", format="multipart", data={"package": file})
        assert response.status_code == 200, f"error: {response.json()['detail']}"

        assert response.json()["app_description"]["name"]
        assert response.json()["app_description"]["code"] == app_code
        assert response.json()["original_app_description"]["code"] == app_code

        response = api_client.post(
            "/api/bkapps/s-mart/confirm/",
            data={"code": app_code, "name": app_code},
        )
        assert response.status_code == 201, f"error: {response.json()['detail']}"

        # Verify app info
        app = Application.objects.get(code=app_code)
        assert app.is_smart_app is True
        assert SMartAppExtraInfo.objects.filter(original_code=app_code, app=app).exists()

    def test_upload_and_create_when_code_exists(self, api_client, tmp_path, bk_app, random_name):
        def _desc_updater(desc):
            desc["app"]["bkAppCode"] = bk_app.code
            desc["app"]["bkAppName"] = bk_app.name
            return desc

        tarball_path = make_smart_tarball(tmp_path, _desc_updater, version="v3")
        with open(tarball_path, "rb") as file:
            response = api_client.post(
                "/api/bkapps/s-mart/",
                format="multipart",
                data={"package": file, "app_tenant_mode": "single"},
            )
        assert response.status_code == 200, f"error: {response.json()['detail']}"

        new_app_code = response.json()["app_description"]["code"]
        assert new_app_code.startswith(f"{bk_app.code}-")
        assert response.json()["original_app_description"]["code"] == bk_app.code

        response = api_client.post(
            "/api/bkapps/s-mart/confirm/",
            data={"code": new_app_code, "name": random_name},
        )
        assert response.status_code == 201, f"error: {response.json()['detail']}"

        # Verify app info
        app = Application.objects.get(code=new_app_code)
        assert app.is_smart_app is True
        assert app.name == random_name

        assert SMartAppExtraInfo.objects.filter(original_code=bk_app.code, app=app).exists()


class TestUpdateSMartApp:
    @pytest.fixture()
    def _create_smart_app(self, bk_cnative_app):
        SMartAppExtraInfo.objects.create(original_code=bk_cnative_app.code, app=bk_cnative_app)
        # AppDeclarativeController.perform_update(desc) 需要 MarketConfig
        MarketConfig.objects.create(
            application=bk_cnative_app,
            enabled=False,
            source_url_type=1,
        )

    @pytest.mark.usefixtures("_create_smart_app")
    def test_stash_and_commit(self, api_client, bk_cnative_app, tmp_path):
        def _desc_updater(desc):
            desc["app"]["bkAppCode"] = bk_cnative_app.code
            desc["app"]["bkAppName"] = bk_cnative_app.name
            return desc

        tarball_path = make_smart_tarball(tmp_path, _desc_updater)

        with open(tarball_path, "rb") as file:
            response = api_client.post(
                f"/api/bkapps/applications/{bk_cnative_app.code}/source_package/stash/",
                format="multipart",
                data={"package": file},
            )
        assert response.json()["app_description"]["code"] == bk_cnative_app.code
        assert response.json()["original_app_description"]["code"] == bk_cnative_app.code

        signature = response.json()["signature"]
        with mock.patch(
            "paasng.platform.declarative.application.controller.AppDeclarativeController._sync_default_module"
        ):
            response = api_client.post(
                f"/api/bkapps/applications/{bk_cnative_app.code}/source_package/commit/{signature}/",
            )

            assert response.status_code == 201


class TestSmartBuilder:
    def test_upload_package(self, api_client, tmp_path, random_name):
        app_code = f"demo-{random_name}"

        def _desc_updater(desc):
            desc["app"]["bkAppCode"] = app_code
            desc["app"]["bkAppName"] = app_code
            return desc

        tarball_path = make_smart_tarball(tmp_path, _desc_updater, version="v3")
        with open(tarball_path, "rb") as file:
            response = api_client.post(reverse("api.tools.s-mart.upload"), format="multipart", data={"package": file})

        assert response.status_code == 200


def make_smart_tarball(tmp_path: Path, desc_updater: Callable, version: str = "") -> Path:
    """Make a S-Mart app tarball file from template(located in "./assets")

    :param desc_updater: the function for modifying app desc payload
    :param version: S-Mart app version, v2 or v3
    """
    tarball_path = tmp_path / "temp.tar.gz"
    tardir_path = tmp_path / "app"

    if version == "v2":
        smart_app_path = SMART_APP_V2_PATH
    else:
        smart_app_path = SMART_APP_V3_PATH

    # Copy and modify
    shutil.copytree(smart_app_path, tardir_path)
    with (tardir_path / "app_desc.yaml.tmpl").open(mode="r") as fp:
        desc = yaml.safe_load(fp.read())
        desc["app"]["region"] = settings.DEFAULT_REGION_NAME

        desc = desc_updater(desc)
        (tardir_path / "app_desc.yaml").write_text(yaml.safe_dump(desc))
        (tardir_path / "main").mkdir(exist_ok=True, parents=True)
        with tarfile.open(tardir_path / "main" / "layer.tar.gz", mode="w:gz"):
            pass

    compress_directory(tardir_path, tarball_path)
    return tarball_path
