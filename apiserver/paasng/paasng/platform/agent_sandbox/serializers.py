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

import re

from django.conf import settings
from rest_framework import serializers

from paasng.platform.applications.models import Application
from paasng.utils.serializers import SafePathField

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
            raise serializers.ValidationError("mount_path must be an absolute path starting with '/'")

        if ".." in value.split("/"):
            raise serializers.ValidationError("mount_path must not contain '..' path segments")

        # 合并连续斜杠，防止 //proc 等绕过黑名单
        normalized = re.sub(r"/+", "/", value).rstrip("/") or "/"
        if normalized == "/":
            raise serializers.ValidationError("mount_path must not be the root directory")

        for deny in settings.AGENT_SANDBOX_MOUNT_PATH_DENY_PREFIXES:
            if normalized == deny or normalized.startswith(deny + "/"):
                raise serializers.ValidationError(f"mount_path must not mount to reserved system directory: {deny}")

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
        # 1) volume_id must not be duplicated
        volume_ids = [item["volume_id"] for item in value]
        if len({str(vid) for vid in volume_ids}) != len(volume_ids):
            raise serializers.ValidationError("volume_id must not be duplicated in volume_mounts")

        # 2) mount_path must not be the same or be a prefix of another (avoid mount point overlap)
        paths = [item["mount_path"] for item in value]
        if len(set(paths)) != len(paths):
            raise serializers.ValidationError("mount_path must not be duplicated in volume_mounts")

        sorted_paths = sorted(paths)
        for i, p in enumerate(sorted_paths):
            for q in sorted_paths[i + 1 :]:
                if q.startswith(p.rstrip("/") + "/"):
                    raise serializers.ValidationError(f"mount_path must not be nested: {p} vs {q}")

        return value


class SandboxCreateOutputSLZ(serializers.ModelSerializer):
    """The serializer for creating sandbox output."""

    class Meta:
        model = Sandbox
        fields = (
            "uuid",
            "name",
            "snapshot",
            "target",
            "env_vars",
            "volume_mounts",
            "cpu",
            "memory",
            "status",
            "created",
            "expired_at",
        )
        extra_kwargs = {
            "uuid": {"label": "沙箱 UUID"},
            "name": {"label": "名称"},
            "snapshot": {"label": "快照镜像"},
            "target": {"label": "目标区域"},
            "env_vars": {"label": "环境变量"},
            "volume_mounts": {"label": "共享挂载"},
            "cpu": {"label": "CPU 上限（核）"},
            "memory": {"label": "内存上限（GB）"},
            "status": {"label": "状态"},
            "created": {"label": "创建时间"},
            "expired_at": {"label": "过期时间"},
        }


class VolumeCreateInputSLZ(serializers.Serializer):
    """The serializer for creating a shared volume."""

    name = serializers.CharField(label="卷名称", max_length=256, help_text="应用内唯一标识")
    display_name = serializers.CharField(
        label="显示名称", max_length=256, required=False, default="", allow_blank=True
    )


class VolumeOutputSLZ(serializers.ModelSerializer):
    """The serializer for volume output."""

    storage_instance_id = serializers.SerializerMethodField(label="存储实例 ID")
    storage_path = serializers.SerializerMethodField(label="存储路径")

    class Meta:
        model = Volume
        fields = ("uuid", "name", "display_name", "application_id", "storage_instance_id", "storage_path", "created")
        extra_kwargs = {
            "uuid": {"label": "卷 UUID"},
            "name": {"label": "卷名称"},
            "display_name": {"label": "显示名称"},
            "application_id": {"label": "应用 ID"},
            "created": {"label": "创建时间"},
        }

    def get_storage_instance_id(self, obj) -> str:
        # 存储实例标识，键名由具体 CSI driver 决定（CFS 为 fsid，NFS 为 server 等）
        attrs = settings.AGENT_SANDBOX_VOLUME_CSI_ATTRIBUTES or {}
        return attrs.get("fsid") or attrs.get("server") or ""

    def get_storage_path(self, obj) -> str:
        return obj.storage_path


class VolumeFileListInputSLZ(serializers.Serializer):
    """列出 volume 内文件(分页)。"""

    path = SafePathField(
        label="路径", required=False, default="", allow_blank=True, help_text="volume 内相对路径，默认根目录"
    )
    is_recursive = serializers.BooleanField(label="递归", required=False, default=False)
    page = serializers.IntegerField(label="页码", required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(label="每页数量", required=False, default=100, min_value=1)
    since = serializers.DateTimeField(label="起始时间", required=False, default=None)
    until = serializers.DateTimeField(label="结束时间", required=False, default=None)

    def validate_page_size(self, value: int) -> int:
        # 上限 500,超限 clamp(与 daemon 侧 maxPageSize 对齐)
        return min(value, 500)


class VolumeFileItemOutputSLZ(serializers.Serializer):
    """列表/元数据中的单个文件条目。"""

    path = SafePathField(label="文件路径")
    name = serializers.CharField(label="文件名")
    is_dir = serializers.BooleanField(label="是否目录")
    size = serializers.IntegerField(label="文件大小（字节）")
    modified_at = serializers.CharField(label="最后修改时间")
    mime = serializers.CharField(label="MIME 类型", allow_blank=True)


class VolumeFileListOutputSLZ(serializers.Serializer):
    """列出volume内文件响应"""

    count = serializers.IntegerField(label="文件总数")
    results = VolumeFileItemOutputSLZ(label="文件列表", many=True)


class VolumeFileStatInputSLZ(serializers.Serializer):
    """查询 volume 内文件元数据。"""

    path = SafePathField(label="路径", help_text="volume 内相对路径")


class VolumeFileStatOutputSLZ(serializers.Serializer):
    """元数据响应。不存在时 exists=false,仍返回 HTTP 200。"""

    exists = serializers.BooleanField(label="是否存在")
    path = serializers.CharField(label="文件路径")
    size = serializers.IntegerField(label="文件大小（字节）", required=False)
    modified_at = serializers.CharField(label="最后修改时间", required=False)
    mime = serializers.CharField(label="MIME 类型", required=False, allow_blank=True)


class VolumeFilePreviewInputSLZ(serializers.Serializer):
    """文本小段预览。"""

    path = SafePathField(label="路径", help_text="volume 内相对路径")
    max_bytes = serializers.IntegerField(label="截断上限(字节)", required=False, default=65536, min_value=1)


class VolumeFileDownloadURLInputSLZ(serializers.Serializer):
    """归档并签发下载/预览 URL"""

    path = SafePathField(label="路径", help_text="volume 内相对路径")
    expires_in = serializers.IntegerField(label="有效期(秒)", required=False, default=600, min_value=1, max_value=3600)


class VolumeFileDownloadURLOutputSLZ(serializers.Serializer):
    """下载/预览 URL 响应"""

    download_url = serializers.CharField(label="下载 URL")
    preview_url = serializers.CharField(label="预览 URL")
    expires_at = serializers.DateTimeField(label="过期时间")
    size = serializers.IntegerField(label="文件大小（字节）")
    sha256 = serializers.CharField(label="文件 SHA256")


class VolumeFileDeleteInputSLZ(serializers.Serializer):
    """删除 volume 内单个文件。"""

    path = SafePathField(label="路径", help_text="volume 内相对路径")


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
