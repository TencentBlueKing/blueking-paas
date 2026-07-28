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

from typing import NamedTuple
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from paasng.platform.agent_sandbox.image_build.constants import ImageType
from paasng.platform.agent_sandbox.models import ImageBuildRecord
from paasng.platform.sandbox_instance.models import SidecarImage
from paasng.platform.sandbox_instance.sidecar_image.views import SidecarImageViewSet

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class MockApp(NamedTuple):
    bk_app_code: str
    verified: bool
    tenant_id: str


@pytest.fixture(autouse=True)
def _set_request_app(monkeypatch):
    """Inject request.app into every request processed by SidecarImageViewSet."""

    def _wrap(original_method):
        def wrapper(self, request, *args, **kwargs):
            request.app = MockApp(bk_app_code="test_client", verified=True, tenant_id="default")
            return original_method(self, request, *args, **kwargs)

        return wrapper

    monkeypatch.setattr(SidecarImageViewSet, "build", _wrap(SidecarImageViewSet.build))
    monkeypatch.setattr(SidecarImageViewSet, "build_status", _wrap(SidecarImageViewSet.build_status))
    monkeypatch.setattr(SidecarImageViewSet, "register", _wrap(SidecarImageViewSet.register))
    monkeypatch.setattr(SidecarImageViewSet, "list", _wrap(SidecarImageViewSet.list))
    monkeypatch.setattr(SidecarImageViewSet, "destroy", _wrap(SidecarImageViewSet.destroy))


class TestSidecarImageBuild:
    def test_build_success(self, sys_aidev_api_client: APIClient):
        """Test submitting a sidecar image build request."""
        with mock.patch(
            "paasng.platform.sandbox_instance.sidecar_image.views.run_sidecar_image_build"
        ) as mock_task:
            mock_task.delay = mock.MagicMock()
            resp = sys_aidev_api_client.post(
                reverse("sidecar_image.build"),
                data={
                    "source_url": "https://example.com/sidecar-source.tar.gz",
                    "image_name": "my-sidecar",
                    "image_tag": "v1.0",
                    "dockerfile_path": "Dockerfile",
                    "docker_build_args": {"BASE_IMAGE": "python:3.11"},
                },
                format="json",
            )
        assert resp.status_code == status.HTTP_201_CREATED
        assert "build_id" in resp.data
        mock_task.delay.assert_called_once()

        build = ImageBuildRecord.objects.get(uuid=resp.data["build_id"])
        assert build.app_code == "test_client"
        assert build.image_name == "my-sidecar"
        assert build.image_tag == "v1.0"
        assert build.docker_build_args == {"BASE_IMAGE": "python:3.11"}
        assert build.image_type == ImageType.SIDECAR.value

    def test_build_invalid_params(self, sys_aidev_api_client: APIClient):
        """Test build with invalid params returns 400."""
        resp = sys_aidev_api_client.post(
            reverse("sidecar_image.build"),
            data={"source_url": "not-a-url", "image_name": "x", "image_tag": "v1"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestSidecarImageBuildStatus:
    def test_build_status_success(self, sys_aidev_api_client: APIClient):
        """Test querying build status by build_id."""
        build = ImageBuildRecord.objects.create(
            app_code="test_client",
            source_url="https://example.com/source.tar.gz",
            image_name="my-sidecar",
            image_tag="v1.0",
            image_type=ImageType.SIDECAR.value,
            tenant_id="default",
        )
        resp = sys_aidev_api_client.get(
            reverse("sidecar_image.build_status", kwargs={"build_id": str(build.uuid)})
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["build_id"] == str(build.uuid)
        assert resp.data["status"] == "pending"

    def test_build_status_not_found(self, sys_aidev_api_client: APIClient):
        """Test querying non-existent build returns 404."""
        resp = sys_aidev_api_client.get(
            reverse("sidecar_image.build_status", kwargs={"build_id": "00000000-0000-0000-0000-000000000000"})
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_build_status_wrong_type(self, sys_aidev_api_client: APIClient):
        """Test querying an agent_sandbox build from sidecar endpoint returns 404."""
        build = ImageBuildRecord.objects.create(
            app_code="test_client",
            source_url="https://example.com/source.tar.gz",
            image_name="sandbox-img",
            image_tag="v1.0",
            image_type=ImageType.AGENT_SANDBOX.value,
            tenant_id="default",
        )
        resp = sys_aidev_api_client.get(
            reverse("sidecar_image.build_status", kwargs={"build_id": str(build.uuid)})
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestSidecarImageRegister:
    def test_register_success(self, sys_aidev_api_client: APIClient):
        """Test registering an existing image as sidecar image."""
        resp = sys_aidev_api_client.post(
            reverse("sidecar_image.register"),
            data={
                "image": "registry.example.com/ns/openclaw:latest",
                "name": "openclaw",
                "tag": "latest",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["image"] == "registry.example.com/ns/openclaw:latest"
        assert resp.data["name"] == "openclaw"
        assert resp.data["tag"] == "latest"
        assert resp.data["build_id"] is None

        # Verify DB record
        assert SidecarImage.objects.filter(
            app_code="test_client", image="registry.example.com/ns/openclaw:latest"
        ).exists()

    def test_register_idempotent(self, sys_aidev_api_client: APIClient):
        """Test registering the same image twice is idempotent."""
        data = {
            "image": "registry.example.com/ns/agent:v2",
            "name": "agent",
            "tag": "v2",
        }
        resp1 = sys_aidev_api_client.post(reverse("sidecar_image.register"), data=data, format="json")
        resp2 = sys_aidev_api_client.post(reverse("sidecar_image.register"), data=data, format="json")
        assert resp1.status_code == status.HTTP_201_CREATED
        assert resp2.status_code == status.HTTP_201_CREATED
        assert resp1.data["id"] == resp2.data["id"]

        # Should only have one record
        assert SidecarImage.objects.filter(app_code="test_client", image=data["image"]).count() == 1


class TestSidecarImageList:
    @pytest.fixture(autouse=True)
    def _images(self):
        """Create some SidecarImage records for list tests."""
        SidecarImage.objects.create(
            app_code="test_client",
            image="registry.example.com/ns/img1:v1",
            name="img1",
            tag="v1",
            tenant_id="default",
        )
        SidecarImage.objects.create(
            app_code="test_client",
            image="registry.example.com/ns/img2:v2",
            name="img2",
            tag="v2",
            tenant_id="default",
        )
        SidecarImage.objects.create(
            app_code="other_client",
            image="registry.example.com/ns/img3:v3",
            name="img3",
            tag="v3",
            tenant_id="default",
        )

    def test_list_all(self, sys_aidev_api_client: APIClient):
        """Test listing all sidecar images for the current app."""
        resp = sys_aidev_api_client.get(reverse("sidecar_image.list"))
        assert resp.status_code == status.HTTP_200_OK
        # Should only return images for test_client, not other_client
        assert len(resp.data) == 2

    def test_list_filter_by_name(self, sys_aidev_api_client: APIClient):
        """Test filtering by name."""
        resp = sys_aidev_api_client.get(reverse("sidecar_image.list"), data={"name": "img1"})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["name"] == "img1"

    def test_list_filter_by_tag(self, sys_aidev_api_client: APIClient):
        """Test filtering by tag."""
        resp = sys_aidev_api_client.get(reverse("sidecar_image.list"), data={"tag": "v2"})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["tag"] == "v2"


class TestSidecarImageDestroy:
    def test_destroy_success(self, sys_aidev_api_client: APIClient):
        """Test deleting a sidecar image record."""
        image = SidecarImage.objects.create(
            app_code="test_client",
            image="registry.example.com/ns/to-delete:v1",
            name="to-delete",
            tag="v1",
            tenant_id="default",
        )
        resp = sys_aidev_api_client.delete(
            reverse("sidecar_image.destroy", kwargs={"image_id": str(image.uuid)})
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not SidecarImage.objects.filter(uuid=image.uuid).exists()

    def test_destroy_not_found(self, sys_aidev_api_client: APIClient):
        """Test deleting a non-existent image returns 404."""
        resp = sys_aidev_api_client.delete(
            reverse("sidecar_image.destroy", kwargs={"image_id": "00000000-0000-0000-0000-000000000000"})
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
