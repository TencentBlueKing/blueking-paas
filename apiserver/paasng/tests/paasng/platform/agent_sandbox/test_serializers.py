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

import pytest
from rest_framework import serializers

from paasng.platform.agent_sandbox.serializers import (
    SandboxCreateInputSLZ,
    SandboxEnvVarsField,
    SandboxVolumeMountInputSLZ,
)


class DummyEnvSerializer(serializers.Serializer):
    env_vars = SandboxEnvVarsField(required=False, default=dict)


def test_env_vars_must_be_object():
    slz = DummyEnvSerializer(data={"env_vars": "not-object"})
    assert not slz.is_valid()
    assert str(slz.errors["env_vars"][0]) == "env must be an object"


@pytest.mark.parametrize(
    "env_value",
    [{1: "one"}, {"FOO": 1}, {"FOO": "BAR", "COUNT": 1}],
)
def test_env_vars_must_be_string_mapping(env_value):
    slz = DummyEnvSerializer(data={"env_vars": env_value})

    assert not slz.is_valid()
    assert str(slz.errors["env_vars"][0]) == "env must be an object of string key-value pairs"


def test_env_vars_accepts_string_mapping():
    env = {"FOO": "BAR", "EMPTY": ""}
    slz = DummyEnvSerializer(data={"env_vars": env})

    slz.is_valid(raise_exception=True)
    assert slz.validated_data["env_vars"] == env


class TestSandboxVolumeMountInputSLZ:
    """Covers volume_id/mount_path validation for a single volume mount item."""

    def test_accepts_valid_volume_id_and_path(self):
        vid = uuid.uuid4()
        slz = SandboxVolumeMountInputSLZ(data={"volume_id": str(vid), "mount_path": "/workspace/data"})
        slz.is_valid(raise_exception=True)
        assert slz.validated_data["volume_id"] == vid
        assert slz.validated_data["mount_path"] == "/workspace/data"

    def test_rejects_invalid_uuid(self):
        slz = SandboxVolumeMountInputSLZ(data={"volume_id": "not-a-uuid", "mount_path": "/workspace/data"})
        assert not slz.is_valid()
        assert "volume_id" in slz.errors

    def test_rejects_relative_path(self):
        slz = SandboxVolumeMountInputSLZ(data={"volume_id": str(uuid.uuid4()), "mount_path": "workspace/data"})
        assert not slz.is_valid()
        assert "mount_path" in slz.errors

    def test_rejects_parent_segment(self):
        slz = SandboxVolumeMountInputSLZ(data={"volume_id": str(uuid.uuid4()), "mount_path": "/workspace/../etc"})
        assert not slz.is_valid()
        assert "mount_path" in slz.errors

    @pytest.mark.parametrize("path", ["/", "///"])
    def test_rejects_root(self, path):
        slz = SandboxVolumeMountInputSLZ(data={"volume_id": str(uuid.uuid4()), "mount_path": path})
        assert not slz.is_valid()
        assert "mount_path" in slz.errors

    @pytest.mark.parametrize(
        "path",
        ["/proc", "/proc/self", "/etc/passwd", "/var/run", "/usr/local/bin", "/tmp/x"],
    )
    def test_rejects_system_reserved_prefix(self, path):
        slz = SandboxVolumeMountInputSLZ(data={"volume_id": str(uuid.uuid4()), "mount_path": path})
        assert not slz.is_valid()
        assert "mount_path" in slz.errors

    def test_normalizes_trailing_slash(self):
        slz = SandboxVolumeMountInputSLZ(data={"volume_id": str(uuid.uuid4()), "mount_path": "/workspace/data/"})
        slz.is_valid(raise_exception=True)
        assert slz.validated_data["mount_path"] == "/workspace/data"


class TestSandboxCreateInputVolumeMounts:
    """Covers the list-level validate_volume_mounts rules on SandboxCreateInputSLZ."""

    def test_empty_list_is_allowed(self):
        slz = SandboxCreateInputSLZ(data={"volume_mounts": []})
        slz.is_valid(raise_exception=True)
        assert slz.validated_data["volume_mounts"] == []

    def test_missing_field_defaults_to_empty(self):
        slz = SandboxCreateInputSLZ(data={})
        slz.is_valid(raise_exception=True)
        assert slz.validated_data["volume_mounts"] == []

    def test_accepts_two_different_volumes(self):
        slz = SandboxCreateInputSLZ(
            data={
                "volume_mounts": [
                    {"volume_id": str(uuid.uuid4()), "mount_path": "/workspace/shared"},
                    {"volume_id": str(uuid.uuid4()), "mount_path": "/opt/data"},
                ]
            }
        )
        slz.is_valid(raise_exception=True)
        assert len(slz.validated_data["volume_mounts"]) == 2

    def test_rejects_duplicate_volume_id(self):
        vid = uuid.uuid4()
        slz = SandboxCreateInputSLZ(
            data={
                "volume_mounts": [
                    {"volume_id": str(vid), "mount_path": "/workspace/a"},
                    {"volume_id": str(vid), "mount_path": "/workspace/b"},
                ]
            }
        )
        assert not slz.is_valid()
        assert "volume_mounts" in slz.errors

    def test_rejects_duplicate_mount_path(self):
        slz = SandboxCreateInputSLZ(
            data={
                "volume_mounts": [
                    {"volume_id": str(uuid.uuid4()), "mount_path": "/workspace/shared"},
                    {"volume_id": str(uuid.uuid4()), "mount_path": "/workspace/shared"},
                ]
            }
        )
        assert not slz.is_valid()
        assert "volume_mounts" in slz.errors

    def test_rejects_parent_child_prefix(self):
        slz = SandboxCreateInputSLZ(
            data={
                "volume_mounts": [
                    {"volume_id": str(uuid.uuid4()), "mount_path": "/workspace"},
                    {"volume_id": str(uuid.uuid4()), "mount_path": "/workspace/platform"},
                ]
            }
        )
        assert not slz.is_valid()
        assert "volume_mounts" in slz.errors
