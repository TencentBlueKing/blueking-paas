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
# and limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from unittest import mock

import pytest

from paasng.platform.agent_sandbox.exceptions import SandboxImageValidateError
from paasng.platform.agent_sandbox.image_validator import check_snapshot_image_exists
from paasng.utils.moby_distribution.registry.exceptions import UnSupportMediaType


class TestCheckSnapshotImageExists:
    """Test check_snapshot_image_exists function."""

    @mock.patch("paasng.platform.agent_sandbox.image_validator.settings")
    @mock.patch("paasng.platform.agent_sandbox.image_validator.ManifestRef")
    @mock.patch("paasng.platform.agent_sandbox.image_validator.DockerRegistryV2Client")
    def test_image_exists(self, mock_client_cls, mock_manifest_ref_cls, mock_settings):
        """Test that no error is raised when image exists in registry."""
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST = "registry.example.com"
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_USERNAME = "user"
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_PASSWORD = "pass"
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_SKIP_TLS_VERIFY = False

        mock_manifest_ref = mock.MagicMock()
        mock_manifest_ref.get_metadata.return_value = mock.MagicMock()  # not None = exists
        mock_manifest_ref_cls.return_value = mock_manifest_ref

        # Should not raise
        check_snapshot_image_exists("registry.example.com/my-image:v1")

    @mock.patch("paasng.platform.agent_sandbox.image_validator.settings")
    @mock.patch("paasng.platform.agent_sandbox.image_validator.ManifestRef")
    @mock.patch("paasng.platform.agent_sandbox.image_validator.DockerRegistryV2Client")
    def test_image_not_found(self, mock_client_cls, mock_manifest_ref_cls, mock_settings):
        """Test that SandboxImageValidateError is raised when image doesn't exist."""
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST = "registry.example.com"
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_USERNAME = "user"
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_PASSWORD = "pass"
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_SKIP_TLS_VERIFY = False

        mock_manifest_ref = mock.MagicMock()
        mock_manifest_ref.get_metadata.return_value = None  # None = not found
        mock_manifest_ref_cls.return_value = mock_manifest_ref

        with pytest.raises(SandboxImageValidateError, match="does not exist"):
            check_snapshot_image_exists("registry.example.com/my-image:v1")

    @mock.patch("paasng.platform.agent_sandbox.image_validator.settings")
    def test_external_registry_rejected(self, mock_settings):
        """Test that images from external registries are rejected."""
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST = "registry.example.com"

        with pytest.raises(SandboxImageValidateError, match="external registry"):
            check_snapshot_image_exists("docker.io/library/python:3.11")

    @mock.patch("paasng.platform.agent_sandbox.image_validator.settings")
    @mock.patch("paasng.platform.agent_sandbox.image_validator.ManifestRef")
    @mock.patch("paasng.platform.agent_sandbox.image_validator.DockerRegistryV2Client")
    def test_registry_error_raises(self, mock_client_cls, mock_manifest_ref_cls, mock_settings):
        """Test that registry errors raise SandboxImageValidateError instead of being silently skipped."""
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST = "registry.example.com"
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_USERNAME = "user"
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_PASSWORD = "pass"
        mock_settings.AGENT_SANDBOX_DOCKER_REGISTRY_SKIP_TLS_VERIFY = False

        mock_manifest_ref = mock.MagicMock()
        mock_manifest_ref.get_metadata.side_effect = ConnectionError("network error")
        mock_manifest_ref_cls.return_value = mock_manifest_ref

        with pytest.raises(SandboxImageValidateError, match="Failed to check existence"):
            check_snapshot_image_exists("registry.example.com/my-image:v1")
