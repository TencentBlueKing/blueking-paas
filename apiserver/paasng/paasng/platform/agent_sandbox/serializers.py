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

import re

from django.conf import settings
from rest_framework import serializers

from paasng.platform.applications.models import Application

from .constants import SANDBOX_DEFAULT_TTL_SECONDS, SANDBOX_MAX_TTL_SECONDS
from .models import Sandbox, Volume



class SandboxVolumeMountInputSLZ(serializers.Serializer):
    """Single shared volume mount request item.

    - ``volume_id`` references a previously created Volume; the platform resolves
      the CFS subPath from the Volume record.
    - ``mount_path`` is the target directory inside the container; subPath and
      readOnly are decided by the platform and not exposed to users.
    """

    volume_id = serializers.UUIDField(label="共享卷 ID", help_text="已创建的 Volume 的 UUID")
    mount_path = serializers.CharField(
        label="容器内挂载路径",
        max_length=256,
        help_text="必须是以 / 开头的合法绝对路径，不可为根目录或落入系统保留目录",
    )

    def validate_volume_id(self, value):
        """将 UUID 对象转为字符串，确保存入 JSONField 时可序列化。"""
        return str(value)

    def validate_mount_path(self, value: str) -> str:
        if not value.startswith("/"):
            raise serializers.ValidationError("mount_path 必须为以 / 开头的绝对路径")
        if ".." in value.split("/"):
            raise serializers.ValidationError("mount_path 不允许包含 '..' 路径段")
        # 合并连续斜杠，防止 //proc 等绕过黑名单
        normalized = re.sub(r"/+", "/", value).rstrip("/") or "/"
        if normalized == "/":
            raise serializers.ValidationError("mount_path 不允许为根目录")
        for deny in settings.AGENT_SANDBOX_MOUNT_PATH_DENY_PREFIXES:
            if normalized == deny or normalized.startswith(deny + "/"):
                raise serializers.ValidationError(f"mount_path 不允许挂载到系统保留目录：{deny}")
        return normalized


class SandboxEnvVarsField(serializers.JSONField):
    """A JSON object field for sandbox environment variables."""

    default_error_messages = {
        "invalid_type": "env must be an object",
        "invalid_item_type": "env must be an object of string key-value pairs",
    }

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not isinstance(value, dict):
            self.fail("invalid_type")
        if any(not isinstance(key, str) or not isinstance(item, str) for key, item in value.items()):
            self.fail("invalid_item_type")
        return value


class SandboxCreateInputSLZ(serializers.Serializer):
    """The serializer for creating sandbox."""

    name = serializers.CharField(label="名称", max_length=64, required=False, help_text="不提供则基于 UUID 生成")
    env_vars = SandboxEnvVarsField(
        label="环境变量", required=False, default=dict, help_text="用于注入到沙箱内的环境变量"
    )
    snapshot = serializers.CharField(
        label="快照镜像", max_length=256, required=False, help_text="沙箱使用的快照镜像，不提供则使用默认镜像"
    )
    snapshot_entrypoint = serializers.ListField(
        child=serializers.CharField(),
        label="快照入口命令",
        required=False,
        help_text="快照镜像的入口命令列表",
    )
    workspace = serializers.CharField(label="工作目录", max_length=256, required=False, help_text="沙箱的工作目录路径")
    ttl_seconds = serializers.IntegerField(
        label="存活时长（秒）",
        required=False,
        default=SANDBOX_DEFAULT_TTL_SECONDS,
        min_value=0,
        max_value=SANDBOX_MAX_TTL_SECONDS,
        help_text="沙箱存活时长（秒）",
    )
    volume_mounts = serializers.ListField(
        child=SandboxVolumeMountInputSLZ(),
        label="共享挂载",
        required=False,
        default=list,
        help_text="共享文件挂载配置列表，不提供则不挂载任何共享卷。",
    )

    def validate_volume_mounts(self, value: list[dict]) -> list[dict]:
        if not value:
            return value
        # 1) volume_id 不得重复
        volume_ids = [item["volume_id"] for item in value]
        if len(set(str(vid) for vid in volume_ids)) != len(volume_ids):
            raise serializers.ValidationError("volume_mounts 中 volume_id 不能重复")
        # 2) mount_path 不得互相相同或彼此为前缀（避免挂载点覆盖）
        paths = [item["mount_path"] for item in value]
        if len(set(paths)) != len(paths):
            raise serializers.ValidationError("volume_mounts 中 mount_path 不能重复")
        sorted_paths = sorted(paths)
        for i, p in enumerate(sorted_paths):
            for q in sorted_paths[i + 1:]:
                if q.startswith(p.rstrip("/") + "/"):
                    raise serializers.ValidationError(
                        f"volume_mounts 中 mount_path 不能互为父目录：{p} vs {q}"
                    )
        return value


class SandboxCreateOutputSLZ(serializers.ModelSerializer):
    """The serializer for creating sandbox output."""

    class Meta:
        model = Sandbox
        fields = ("uuid", "name", "snapshot", "target", "env_vars", "volume_mounts", "cpu", "memory", "status", "created", "expired_at")


class VolumeCreateInputSLZ(serializers.Serializer):
    """The serializer for creating a shared volume."""

    name = serializers.CharField(label="卷名称", max_length=64, help_text="应用内唯一标识")
    display_name = serializers.CharField(label="显示名称", max_length=128, required=False, default="", allow_blank=True)


class VolumeOutputSLZ(serializers.ModelSerializer):
    """The serializer for volume output."""

    cfs_instance_id = serializers.SerializerMethodField()
    cfs_path = serializers.SerializerMethodField()

    class Meta:
        model = Volume
        fields = ("uuid", "name", "display_name", "application_id", "cfs_instance_id", "cfs_path", "created")

    def get_cfs_instance_id(self, obj) -> str:
        return settings.AGENT_SANDBOX_CFS_FSID

    def get_cfs_path(self, obj) -> str:
        return obj.cfs_path


class SandboxCreateFolderInputSLZ(serializers.Serializer):
    """The serializer for creating folder in sandbox."""

    path = serializers.CharField(label="目录路径", help_text="要创建的目录路径")
    mode = serializers.RegexField(
        regex=r"^[0-7]{3,4}$",
        label="目录权限",
        default="755",
        required=False,
        help_text="目录权限（八进制），默认 755",
    )


class SandboxUploadFileInputSLZ(serializers.Serializer):
    """The serializer for uploading file to sandbox."""

    path = serializers.CharField(label="远端路径", help_text="文件在沙箱中的目标路径")
    file = serializers.FileField(label="文件", help_text="待上传文件内容")


class SandboxDeleteFileInputSLZ(serializers.Serializer):
    """The serializer for deleting file/folder in sandbox."""

    path = serializers.CharField(label="路径", help_text="待删除文件或目录路径")
    recursive = serializers.BooleanField(
        label="递归删除",
        required=False,
        default=False,
        help_text="删除目录时是否递归删除（默认否）",
    )


class SandboxDownloadFileInputSLZ(serializers.Serializer):
    """The serializer for downloading file from sandbox."""

    path = serializers.CharField(label="路径", help_text="待下载文件路径")


class SandboxExecInputSLZ(serializers.Serializer):
    """The serializer for executing command in sandbox."""

    cmd = serializers.JSONField(label="命令", help_text="执行命令，支持字符串或字符串列表")
    cwd = serializers.CharField(
        label="工作目录",
        required=False,
        allow_blank=False,
        help_text="命令执行目录，不提供时使用沙箱默认工作目录",
    )
    env_vars = SandboxEnvVarsField(label="环境变量", required=False, default=dict, help_text="命令执行环境变量")
    # timeout 需要小于蓝鲸网关的默认最大超时时间 300s
    timeout = serializers.IntegerField(
        label="超时（秒）", required=False, default=296, min_value=1, help_text="执行超时时间"
    )

    def validate_cmd(self, value):
        match value:
            case str() as cmd if cmd.strip():
                return cmd
            case list() as items if items and all(isinstance(item, str) and item for item in items):
                return items
            case _:
                raise serializers.ValidationError("cmd must be a non-empty string or a non-empty list of strings")


class SandboxProcessOutputSLZ(serializers.Serializer):
    """The serializer for command/code execution result in sandbox."""

    stdout = serializers.CharField(label="标准输出", allow_blank=True)
    stderr = serializers.CharField(label="标准错误", allow_blank=True)
    exit_code = serializers.IntegerField(label="退出码")


class SandboxCodeRunInputSLZ(serializers.Serializer):
    """The serializer for running code in sandbox."""

    content = serializers.CharField(label="代码内容", help_text="待执行代码")
    language = serializers.CharField(label="语言", required=False, default="Python", help_text="代码语言，默认 Python")


class SandboxGetLogsInputSLZ(serializers.Serializer):
    """The serializer for getting sandbox logs."""

    tail_lines = serializers.IntegerField(
        label="返回行数",
        required=False,
        min_value=1,
        max_value=20000,
        help_text="仅返回最后 N 行日志，不提供则返回全部",
    )
    timestamps = serializers.BooleanField(
        label="时间戳",
        required=False,
        default=False,
        help_text="是否在日志前附加时间戳",
    )


class SandboxGetLogsOutputSLZ(serializers.Serializer):
    """The serializer for sandbox logs response."""

    logs = serializers.CharField(label="日志内容", allow_blank=True)


class GrantAgentSandboxPermissionSLZ(serializers.Serializer):
    """The serializer for granting Agent Sandbox API permissions."""

    target_app_code = serializers.CharField(
        label="目标应用 code",
        help_text="待授权应用的 code",
    )
    expire_days = serializers.IntegerField(
        label="过期时间（天）",
        required=False,
        default=0,
        min_value=0,
        help_text="过期时间，0 表示永久权限",
    )

    def validate_target_app_code(self, value: str) -> str:
        if not Application.objects.filter(code=value, is_ai_agent_app=True).exists():
            raise serializers.ValidationError(f"应用 '{value}' 不存在或不是 AI Agent 应用")
        return value
