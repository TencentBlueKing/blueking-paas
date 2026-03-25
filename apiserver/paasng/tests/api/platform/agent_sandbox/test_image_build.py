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

from typing import NamedTuple
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from paasng.platform.agent_sandbox.image_build.constants import ImageBuildStatus
from paasng.platform.agent_sandbox.image_build.views import ImageBuildViewSet
from paasng.platform.agent_sandbox.models import ImageBuild

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class MockApp(NamedTuple):
    bk_app_code: str
    verified: bool
    tenant_id: str


@pytest.fixture(autouse=True)
def _set_request_app(monkeypatch):
    """Inject request.app into every request processed by ImageBuildViewSet.

    In production, request.app is set by ApiGatewayJWTAppMiddleware. Here we
    patch each view method to set it before the original logic runs.
    """

    def _wrap(original_method):
        def wrapper(self, request, *args, **kwargs):
            request.app = MockApp(bk_app_code="test_client", verified=True, tenant_id="default")
            return original_method(self, request, *args, **kwargs)

        return wrapper

    monkeypatch.setattr(ImageBuildViewSet, "create", _wrap(ImageBuildViewSet.create))
    monkeypatch.setattr(ImageBuildViewSet, "retrieve", _wrap(ImageBuildViewSet.retrieve))
    monkeypatch.setattr(ImageBuildViewSet, "list", _wrap(ImageBuildViewSet.list))


class TestImageBuildCreate:
    def test_create_success(self, sys_aidev_api_client: APIClient):
        """Test creating an image build task with both required and optional params."""
        with mock.patch("paasng.platform.agent_sandbox.image_build.views.run_image_build") as mock_task:
            mock_task.delay = mock.MagicMock()
            resp = sys_aidev_api_client.post(
                reverse("image_build.list_create"),
                data={
                    "source_url": "https://example.com/source.tar.gz",
                    "image_name": "my-app",
                    "image_tag": "v1.0",
                    "dockerfile_path": "docker/Dockerfile",
                    "docker_build_args": {"PYTHON_VERSION": "3.11"},
                },
                format="json",
            )
        assert resp.status_code == status.HTTP_201_CREATED
        assert "build_id" in resp.data
        mock_task.delay.assert_called_once()

        build = ImageBuild.objects.get(uuid=resp.data["build_id"])
        assert build.app_code == "test_client"
        assert build.tenant_id == "default"
        assert build.dockerfile_path == "docker/Dockerfile"
        assert build.docker_build_args == {"PYTHON_VERSION": "3.11"}

    def test_create_invalid_params(self, sys_aidev_api_client: APIClient):
        """Test creating with invalid params returns 400."""
        resp = sys_aidev_api_client.post(
            reverse("image_build.list_create"),
            data={"source_url": "not-a-url", "image_name": "my-app", "image_tag": "v1.0"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_permission_denied(self):
        """Test creating without auth returns error (no sysapi client)."""
        client = APIClient()
        resp = client.post(
            reverse("image_build.list_create"),
            data={
                "source_url": "https://example.com/source.tar.gz",
                "image_name": "my-app",
                "image_tag": "v1.0",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestImageBuildRetrieveAndList:
    @pytest.fixture(autouse=True)
    def _build(self):
        """Create a single ImageBuild for retrieve / list tests."""
        self.build = ImageBuild.objects.create(
            app_code="test_client",
            source_url="https://example.com/source.tar.gz",
            image_name="my-app",
            image_tag="v1.0",
            tenant_id="default",
        )

    def test_retrieve(self, sys_aidev_api_client: APIClient):
        resp = sys_aidev_api_client.get(
            reverse("image_build.retrieve", kwargs={"build_id": str(self.build.uuid)}),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["build_id"] == str(self.build.uuid)
        assert resp.data["output_image"] == self.build.output_image
        assert resp.data["status"] == ImageBuildStatus.PENDING.value

    def test_retrieve_not_found(self, sys_aidev_api_client: APIClient):
        resp = sys_aidev_api_client.get(
            reverse("image_build.retrieve", kwargs={"build_id": "00000000-0000-0000-0000-000000000000"}),
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_filtered(self, sys_aidev_api_client: APIClient):
        """Test listing builds filtered by image_name and image_tag."""
        resp = sys_aidev_api_client.get(
            reverse("image_build.list_create"),
            data={"image_name": "my-app", "image_tag": "v1.0"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["output_image"].endswith("my-app:v1.0")
