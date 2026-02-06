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

import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse

from paasng.misc.tools.smart_app.constants import SourceCodeOriginType
from paasng.platform.engine.constants import JobStatus
from tests.conftest import create_user
from tests.paasng.misc.tools.smart_app.setup_utils import create_fake_smart_build

pytestmark = pytest.mark.django_db


class TestSmartBuildHistoryViewSet:
    """Test suite for `SmartBuildHistoryViewSet`"""

    @pytest.fixture
    def smart_build_record(self, bk_user):
        """Create SmartBuild Record instance"""
        return create_fake_smart_build(operator=bk_user)

    def test_list_history(self, api_client, smart_build_record):
        """Test listing build history"""
        url = reverse("api.tools.s-mart.build_records")
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert any(item["uuid"] == str(smart_build_record.uuid) for item in data["results"])

    def test_list_history_by_user(self, api_client, smart_build_record):
        """Test listing build history filtered by operator"""

        # Create a record by a different user
        other_user = create_user()
        other_build = create_fake_smart_build(operator=other_user)

        api_client.force_authenticate(user=other_user)
        url = reverse("api.tools.s-mart.build_records")
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["uuid"] == str(other_build.uuid)

    @pytest.mark.parametrize(
        ("filter_params", "expected_count"),
        [
            ({"source_origin": SourceCodeOriginType.PACKAGE}, 2),
            ({"status": JobStatus.SUCCESSFUL}, 2),
            ({"search": "v2"}, 1),
        ],
    )
    def test_list_history_with_filters(self, filter_params, expected_count, api_client, bk_user):
        """Test listing build history with filters"""
        # Create multiple records with different attributes
        create_fake_smart_build(
            source_origin=SourceCodeOriginType.PACKAGE,
            package_name="app_v1.tar.gz",
            status=JobStatus.SUCCESSFUL,
            operator=bk_user,
        )
        create_fake_smart_build(
            source_origin=SourceCodeOriginType.REPO,
            package_name="app_v2.tar.gz",
            status=JobStatus.FAILED,
            operator=bk_user,
        )
        create_fake_smart_build(
            source_origin=SourceCodeOriginType.PACKAGE,
            package_name="test_app.tar.gz",
            status=JobStatus.SUCCESSFUL,
            operator=bk_user,
        )

        url = reverse("api.tools.s-mart.build_records")
        response = api_client.get(url, filter_params)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == expected_count

    def test_get_history_logs_success(self, api_client, smart_build_record):
        """Test retrieving build logs for a specific build record successfully"""

        with patch("paasng.misc.tools.smart_app.views.get_all_logs") as mock_get_all_logs:
            mock_logs = "This is a test log\nLine 2\nLine 3"
            mock_get_all_logs.return_value = mock_logs

            url = reverse("api.tools.s-mart.build_records.logs", args=[smart_build_record.uuid])
            response = api_client.get(url)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == smart_build_record.status
            assert data["logs"] == mock_logs
            mock_get_all_logs.assert_called_once_with(smart_build_record)

    def test_get_history_logs_not_found(self, api_client):
        """Test retrieving build logs for a non-existent build record"""

        fake_uuid = uuid.uuid4()
        url = reverse("api.tools.s-mart.build_records.logs", kwargs={"uuid": fake_uuid})
        response = api_client.get(url)

        assert response.status_code == 404

    def test_download_history_logs_success(self, api_client, smart_build_record):
        """Test downloading build logs for a specific build record successfully"""

        with patch("paasng.misc.tools.smart_app.views.get_all_logs") as mock_get_all_logs:
            mock_logs = "This is a test log\nLine 2\nLine 3"
            mock_get_all_logs.return_value = mock_logs

            url = reverse("api.tools.s-mart.build_records.logs.download", args=[smart_build_record.uuid])
            response = api_client.get(url, {"download": "true"})

            assert response.status_code == 200
            assert response["Content-Type"] == "text/plain"
            assert (
                response["Content-Disposition"]
                == f'attachment; filename="{smart_build_record.package_name}-{smart_build_record.uuid}.log"'
            )
            assert response.content.decode() == mock_logs
            mock_get_all_logs.assert_called_once_with(smart_build_record)

    def test_download_history_logs_not_found(self, api_client):
        """Test downloading build logs for a non-existent build record"""
        fake_uuid = uuid.uuid4()
        url = reverse("api.tools.s-mart.build_records.logs.download", kwargs={"uuid": fake_uuid})
        response = api_client.get(url)

        assert response.status_code == 404
