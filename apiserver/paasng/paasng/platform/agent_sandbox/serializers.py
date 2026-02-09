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

from rest_framework import serializers

from .models import Sandbox


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
            "cpu",
            "memory",
            "status",
            "created",
        )


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
    timeout = serializers.IntegerField(
        label="超时（秒）", required=False, default=60, min_value=1, help_text="执行超时时间"
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
