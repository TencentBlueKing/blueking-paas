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

import logging
from pathlib import PurePosixPath
from typing import Callable

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.platform.agent_sandbox.exceptions import SandboxAlreadyExists, SandboxError
from paasng.platform.agent_sandbox.models import Sandbox
from paasng.platform.agent_sandbox.sandbox import (
    create_sandbox,
    delete_sandbox,
    get_sandbox_client,
)
from paasng.platform.agent_sandbox.serializers import (
    SandboxCodeRunInputSLZ,
    SandboxCreateFolderInputSLZ,
    SandboxCreateInputSLZ,
    SandboxCreateOutputSLZ,
    SandboxDeleteFileInputSLZ,
    SandboxDownloadFileInputSLZ,
    SandboxExecInputSLZ,
    SandboxGetLogsInputSLZ,
    SandboxGetLogsOutputSLZ,
    SandboxProcessOutputSLZ,
    SandboxUploadFileInputSLZ,
)
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class AgentSandboxViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    """Agent Sandbox 相关接口"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        request_body=SandboxCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: SandboxCreateOutputSLZ()},
    )
    def create(self, request, code):
        """创建一个新的 Agent Sandbox，新沙箱将自动进入运行状态。"""
        # TODO: Add permission check. 最终是应用认证/鉴权+用户认证
        application = self.get_application_without_perm()
        slz = SandboxCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            sandbox = create_sandbox(
                application=application,
                creator=request.user.pk,
                name=data.get("name"),
                env_vars=data.get("env_vars"),
                snapshot=data.get("snapshot"),
                snapshot_entrypoint=data.get("snapshot_entrypoint"),
                workspace=data.get("workspace"),
            )
        except SandboxAlreadyExists:
            raise error_codes.AGENT_SANDBOX_ALREADY_EXISTS
        except SandboxError:
            logger.exception("Failed to create agent sandbox")
            raise error_codes.AGENT_SANDBOX_CREATE_FAILED
        return Response(SandboxCreateOutputSLZ(sandbox).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["agent_sandbox"], responses={status.HTTP_204_NO_CONTENT: ""})
    def destroy(self, request, sandbox_id):
        """停止并销毁一个 Agent Sandbox"""
        sandbox = get_object_or_404(Sandbox, uuid=sandbox_id, deleted_at__isnull=True)
        self.check_object_permissions(request, sandbox.application)

        try:
            delete_sandbox(sandbox)
        except SandboxError:
            logger.exception("Failed to delete agent sandbox")
            raise error_codes.AGENT_SANDBOX_DELETE_FAILED
        return Response(status=status.HTTP_204_NO_CONTENT)


class SandboxPermissionMixin:
    """The Mixin for checking sandbox permissions."""

    check_object_permissions: Callable

    def _get_sandbox_with_perm(self, request, sandbox_id: str) -> Sandbox:
        sandbox = get_object_or_404(Sandbox, uuid=sandbox_id, deleted_at__isnull=True)
        # TODO: Add permission check
        return sandbox


class AgentSandboxFSViewSet(SandboxPermissionMixin, viewsets.GenericViewSet):
    """Agent Sandbox 文件系统相关接口。"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=["agent_sandbox"], request_body=SandboxCreateFolderInputSLZ(), responses={204: ""})
    def create_folder(self, request, sandbox_id):
        """在 Agent Sandbox 中创建目录。"""
        sandbox = self._get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxCreateFolderInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            get_sandbox_client(sandbox).create_folder(path=data["path"], mode=data["mode"])
        except SandboxError:
            logger.exception("Failed to create folder in sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["agent_sandbox"], request_body=SandboxUploadFileInputSLZ(), responses={204: ""})
    def upload_file(self, request, sandbox_id):
        """上传文件到 Agent Sandbox。"""
        sandbox = self._get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxUploadFileInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            get_sandbox_client(sandbox).upload_file(file=data["file"].read(), remote_path=data["path"])
        except SandboxError:
            logger.exception("Failed to upload file to sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["agent_sandbox"], request_body=SandboxDeleteFileInputSLZ(), responses={204: ""})
    def delete_file(self, request, sandbox_id):
        """删除 Agent Sandbox 中的文件或目录。"""
        sandbox = self._get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxDeleteFileInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            get_sandbox_client(sandbox).delete_file(path=data["path"], recursive=data["recursive"])
        except SandboxError:
            logger.exception("Failed to delete file in sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["agent_sandbox"], query_serializer=SandboxDownloadFileInputSLZ(), responses={200: ""})
    def download_file(self, request, sandbox_id):
        """下载 Agent Sandbox 中的文件。"""
        sandbox = self._get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxDownloadFileInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            content = get_sandbox_client(sandbox).download_file(remote_path=data["path"])
        except SandboxError:
            logger.exception("Failed to download file from sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED

        filename = PurePosixPath(data["path"]).name or "sandbox-file"
        response = HttpResponse(content, content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        return response


class AgentSandboxProcessViewSet(SandboxPermissionMixin, viewsets.GenericViewSet):
    """Agent Sandbox 进程相关接口。"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["agent_sandbox"], request_body=SandboxExecInputSLZ(), responses={200: SandboxProcessOutputSLZ()}
    )
    def exec(self, request, sandbox_id):
        """在 Agent Sandbox 内执行命令。"""
        sandbox = self._get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxExecInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            result = get_sandbox_client(sandbox).exec(
                cmd=data["cmd"],
                cwd=data.get("cwd"),
                env_vars=data["env_vars"],
                timeout=data["timeout"],
            )
        except SandboxError:
            logger.exception("Failed to execute command in sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_PROCESS_OPERATION_FAILED
        return Response(SandboxProcessOutputSLZ(result).data)

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        request_body=SandboxCodeRunInputSLZ(),
        responses={200: SandboxProcessOutputSLZ()},
    )
    def code_run(self, request, sandbox_id):
        """在 Agent Sandbox 内执行代码片段。"""
        sandbox = self._get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxCodeRunInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            result = get_sandbox_client(sandbox).code_run(content=data["content"], language=data["language"])
        except SandboxError:
            logger.exception("Failed to run code in sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_PROCESS_OPERATION_FAILED
        return Response(SandboxProcessOutputSLZ(result).data)

    @swagger_auto_schema(
        tags=["agent_sandbox"], query_serializer=SandboxGetLogsInputSLZ(), responses={200: SandboxGetLogsOutputSLZ()}
    )
    def logs(self, request, sandbox_id):
        """读取 Agent Sandbox 日志。"""
        sandbox = self._get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxGetLogsInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            logs = get_sandbox_client(sandbox).get_logs(
                tail_lines=data.get("tail_lines"),
                timestamps=data["timestamps"],
            )
        except SandboxError:
            logger.exception("Failed to get logs from sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_PROCESS_OPERATION_FAILED
        return Response(SandboxGetLogsOutputSLZ({"logs": logs}).data)
