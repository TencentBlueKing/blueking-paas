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

import logging
from datetime import timedelta
from pathlib import PurePosixPath
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.cloudapi_v2.apigateway.clients import ApiGatewayClient
from paasng.accessories.cloudapi_v2.apigateway.exceptions import ApiGatewayServiceError
from paasng.infras.accounts.utils import ForceAllowAuthedApp
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.platform.agent_sandbox.artifact import archive_volume_file, build_download_url, delete_volume_artifact
from paasng.platform.agent_sandbox.exceptions import (
    SandboxAlreadyExists,
    SandboxArchiveFailed,
    SandboxCreateError,
    SandboxError,
    SandboxExecTimeout,
    SandboxFileNotFound,
    SandboxFileNotPreviewable,
    SandboxFileTooLarge,
    SandboxImageValidateError,
    SandboxServiceNotReady,
)
from paasng.platform.agent_sandbox.mixins import SandboxViewMixin
from paasng.platform.agent_sandbox.models import Volume
from paasng.platform.agent_sandbox.permissions import IsAPIGWVerifiedApp
from paasng.platform.agent_sandbox.resident_daemon_client import get_resident_daemon_client
from paasng.platform.agent_sandbox.sandbox import (
    create_sandbox,
    delete_sandbox,
    get_sandbox_client,
)
from paasng.platform.agent_sandbox.serializers import (
    GrantAgentSandboxPermissionSLZ,
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
    VolumeCreateInputSLZ,
    VolumeFileDeleteInputSLZ,
    VolumeFileDownloadURLInputSLZ,
    VolumeFileDownloadURLOutputSLZ,
    VolumeFileListInputSLZ,
    VolumeFileListOutputSLZ,
    VolumeFilePreviewInputSLZ,
    VolumeFileStatInputSLZ,
    VolumeFileStatOutputSLZ,
    VolumeOutputSLZ,
)
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class VolumeViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    """Volume 共享存储卷相关接口"""

    permission_classes = [IsAuthenticated, IsAPIGWVerifiedApp]

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        request_body=VolumeCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: VolumeOutputSLZ()},
    )
    def create(self, request, code):
        """创建共享存储卷。"""
        application = self.get_application()
        slz = VolumeCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        if Volume.objects.filter(application=application, name=data["name"], deleted_at__isnull=True).exists():
            raise error_codes.AGENT_SANDBOX_VOLUME_ALREADY_EXISTS

        try:
            volume = Volume.objects.create(
                application=application,
                name=data["name"],
                display_name=data.get("display_name", ""),
                tenant_id=application.tenant_id,
            )
        except Exception:
            logger.exception("Failed to create volume for app %s", application.code)
            raise error_codes.AGENT_SANDBOX_VOLUME_CREATE_FAILED
        return Response(VolumeOutputSLZ(volume).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["agent_sandbox"], responses={status.HTTP_204_NO_CONTENT: ""})
    def destroy(self, request, code, volume_id):
        """软删除共享存储卷。"""
        application = self.get_application()
        volume = get_object_or_404(Volume, uuid=volume_id, application=application, deleted_at__isnull=True)
        # TODO: 检查是否有沙箱正在使用该 Volume，有则阻止删除
        # TODO: CFS 数据清理流程
        volume.deleted_at = timezone.now()
        volume.save(update_fields=["deleted_at", "updated"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        responses={status.HTTP_200_OK: VolumeOutputSLZ(many=True)},
    )
    def list(self, request, code):
        """查询应用的可用共享存储卷列表。"""
        application = self.get_application()
        volumes = Volume.objects.filter(application=application, deleted_at__isnull=True).order_by("-created")
        return Response(VolumeOutputSLZ(volumes, many=True).data)


class VolumeFileViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    """Volume 文件持久化相关接口

    面向 AIDev 前端提供沙箱销毁后仍可访问的产物文件的 列表 / 元数据 / 文本预览 /
    下载(预览)URL / 删除。数据(下载)走 bkrepo 签名 URL直连, 归档由常驻 daemon
    直连 bkrepo 上传,apiserver 仅编排、签发临时 URL。

    paas-apiserver --> 常驻 daemon --> bkrepo --> 响应
                            |
                           CFS
    """

    permission_classes = [IsAuthenticated]

    def _get_volume(self, volume_id: str) -> Volume:
        """校验 app 归属并返回未删除的 Volume。

        get_application() 触发 IsAPIGWVerifiedApp 的对象级校验(来源 app 必须与目标 app 一致),
        再按 application 过滤 volume, 保证 app 之间的隔离。
        """
        application = self.get_application()
        return get_object_or_404(Volume, uuid=volume_id, application=application, deleted_at__isnull=True)

    def _validate(self, slz_cls, data) -> dict:
        """实例化序列化器并校验,返回 validated_data。"""
        slz = slz_cls(data=data)
        slz.is_valid(raise_exception=True)
        return slz.validated_data

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        query_serializer=VolumeFileListInputSLZ(),
        responses={status.HTTP_200_OK: VolumeFileListOutputSLZ()},
    )
    def list(self, request, code, volume_id):
        """列出 volume 内文件(分页)。"""
        volume = self._get_volume(volume_id)
        data = self._validate(VolumeFileListInputSLZ, request.query_params)

        try:
            result = get_resident_daemon_client().list(
                base_path=volume.storage_path,
                rel_path=data["path"],
                recursive=data["recursive"],
                page=data["page"],
                page_size=data["page_size"],
            )
        except SandboxFileNotFound:
            raise error_codes.AGENT_SANDBOX_FILE_NOT_FOUND
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to list files in volume: %s", volume.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED
        return Response(VolumeFileListOutputSLZ(result).data)

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        query_serializer=VolumeFileStatInputSLZ(),
        responses={status.HTTP_200_OK: VolumeFileStatOutputSLZ()},
    )
    def stat(self, request, code, volume_id):
        """查询 volume 内文件元数据(不存在时返回 200 + exists=false)。"""
        volume = self._get_volume(volume_id)
        data = self._validate(VolumeFileStatInputSLZ, request.query_params)

        try:
            result = get_resident_daemon_client().stat(base_path=volume.storage_path, rel_path=data["path"])
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to stat file in volume: %s", volume.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED
        return Response(VolumeFileStatOutputSLZ(result).data)

    @swagger_auto_schema(tags=["agent_sandbox"], query_serializer=VolumeFilePreviewInputSLZ(), responses={200: ""})
    def preview(self, request, code, volume_id):
        """文本小段预览。忠实透传 daemon 的 text/plain body 与 X-Truncated header。"""
        volume = self._get_volume(volume_id)
        data = self._validate(VolumeFilePreviewInputSLZ, request.query_params)

        try:
            content, truncated = get_resident_daemon_client().preview(
                base_path=volume.storage_path, rel_path=data["path"], max_bytes=data["max_bytes"]
            )
        except SandboxFileNotFound:
            raise error_codes.AGENT_SANDBOX_FILE_NOT_FOUND
        except SandboxFileNotPreviewable:
            raise error_codes.AGENT_SANDBOX_FILE_NOT_PREVIEWABLE
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to preview file in volume: %s", volume.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED

        # 透传原始文本，手动设置 content_type
        response = HttpResponse(content, content_type="text/plain; charset=utf-8")
        response["X-Truncated"] = "true" if truncated else "false"
        response["Access-Control-Expose-Headers"] = "X-Truncated"
        return response

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        query_serializer=VolumeFileDownloadURLInputSLZ(),
        responses={status.HTTP_200_OK: VolumeFileDownloadURLOutputSLZ()},
    )
    def download_url(self, request, code, volume_id):
        """归档到 bkrepo(按需)并签发下载/预览 URL,一次返回两个互斥 URL。

        ``download_url`` 带 ``download=true``(attachment),``preview_url`` 带 ``preview=true``(inline)。
        """
        volume = self._get_volume(volume_id)
        data = self._validate(VolumeFileDownloadURLInputSLZ, request.query_params)

        try:
            artifact = archive_volume_file(volume, data["path"])
            base_url = build_download_url(artifact, expires_in=data["expires_in"])
            sep = "&" if urlparse(base_url).query else "?"
            download_url = f"{base_url}{sep}{urlencode({'download': 'true'})}"
            preview_url = f"{base_url}{sep}{urlencode({'preview': 'true'})}"
        except SandboxFileNotFound:
            raise error_codes.AGENT_SANDBOX_FILE_NOT_FOUND
        except SandboxFileTooLarge:
            raise error_codes.AGENT_SANDBOX_FILE_TOO_LARGE
        except SandboxArchiveFailed:
            logger.exception("Failed to archive file in volume: %s", volume.uuid)
            raise error_codes.AGENT_SANDBOX_ARCHIVE_FAILED
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to build download url for volume: %s", volume.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED

        return Response(
            VolumeFileDownloadURLOutputSLZ(
                {
                    "download_url": download_url,
                    "preview_url": preview_url,
                    "expires_at": timezone.now() + timedelta(seconds=data["expires_in"]),
                    "size": artifact.size,
                    "sha256": artifact.sha256,
                }
            ).data
        )

    @swagger_auto_schema(
        tags=["agent_sandbox"], query_serializer=VolumeFileDeleteInputSLZ(), responses={status.HTTP_200_OK: ""}
    )
    def destroy(self, request, code, volume_id):
        """删除 volume 内单个文件(幂等)。"""
        volume = self._get_volume(volume_id)
        data = self._validate(VolumeFileDeleteInputSLZ, request.query_params)

        try:
            get_resident_daemon_client().delete(base_path=volume.storage_path, rel_path=data["path"])
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to delete file in volume: %s", volume.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED

        # 清理 bkrepo 对象 + 去重表记录, 避免下次归档命中陈旧映射 / "Node existed"
        delete_volume_artifact(volume, data["path"])
        return Response({"deleted": True})


class AgentSandboxViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin, SandboxViewMixin):
    """Agent Sandbox 相关接口"""

    permission_classes = [IsAuthenticated, IsAPIGWVerifiedApp]

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        request_body=SandboxCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: SandboxCreateOutputSLZ()},
    )
    def create(self, request, code):
        """创建一个新的 Agent Sandbox，新沙箱将自动进入运行状态。"""
        application = self.get_application()
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
                ttl_seconds=data["ttl_seconds"],
                volume_mounts=data.get("volume_mounts"),
            )
        except SandboxAlreadyExists:
            raise error_codes.AGENT_SANDBOX_ALREADY_EXISTS
        except SandboxImageValidateError as e:
            raise error_codes.AGENT_SANDBOX_IMAGE_VALIDATE_FAILED.f(str(e))
        except SandboxCreateError as e:
            raise error_codes.AGENT_SANDBOX_CREATE_FAILED.set_data({"logs": e.logs})
        except SandboxError:
            logger.exception("Failed to create agent sandbox")
            raise error_codes.AGENT_SANDBOX_CREATE_FAILED
        return Response(SandboxCreateOutputSLZ(sandbox).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["agent_sandbox"], responses={status.HTTP_204_NO_CONTENT: ""})
    def destroy(self, request, sandbox_id):
        """停止并销毁一个 Agent Sandbox"""
        sandbox = self.get_sandbox_with_perm(request, sandbox_id)

        try:
            delete_sandbox(sandbox)
        except SandboxError:
            logger.exception("Failed to delete agent sandbox")
            raise error_codes.AGENT_SANDBOX_DELETE_FAILED
        return Response(status=status.HTTP_204_NO_CONTENT)


class AgentSandboxFSViewSet(SandboxViewMixin, viewsets.GenericViewSet):
    """Agent Sandbox 文件系统相关接口。"""

    permission_classes = [IsAuthenticated, IsAPIGWVerifiedApp]

    @swagger_auto_schema(tags=["agent_sandbox"], request_body=SandboxCreateFolderInputSLZ(), responses={204: ""})
    def create_folder(self, request, sandbox_id):
        """在 Agent Sandbox 中创建目录。"""
        sandbox = self.get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxCreateFolderInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            get_sandbox_client(sandbox).create_folder(path=data["path"], mode=data["mode"])
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to create folder in sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["agent_sandbox"], request_body=SandboxUploadFileInputSLZ(), responses={204: ""})
    def upload_file(self, request, sandbox_id):
        """上传文件到 Agent Sandbox。"""
        sandbox = self.get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxUploadFileInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            get_sandbox_client(sandbox).upload_file(file=data["file"].read(), remote_path=data["path"])
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to upload file to sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["agent_sandbox"], request_body=SandboxDeleteFileInputSLZ(), responses={204: ""})
    def delete_file(self, request, sandbox_id):
        """删除 Agent Sandbox 中的文件或目录。"""
        sandbox = self.get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxDeleteFileInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            get_sandbox_client(sandbox).delete_file(path=data["path"], recursive=data["recursive"])
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to delete file in sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["agent_sandbox"], query_serializer=SandboxDownloadFileInputSLZ(), responses={200: ""})
    def download_file(self, request, sandbox_id):
        """下载 Agent Sandbox 中的文件。"""
        sandbox = self.get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxDownloadFileInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            content = get_sandbox_client(sandbox).download_file(remote_path=data["path"])
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to download file from sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_FILE_OPERATION_FAILED

        filename = PurePosixPath(data["path"]).name or "sandbox-file"
        response = HttpResponse(content, content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        return response


class AgentSandboxProcessViewSet(SandboxViewMixin, viewsets.GenericViewSet):
    """Agent Sandbox 进程相关接口。"""

    permission_classes = [IsAuthenticated, IsAPIGWVerifiedApp]

    @swagger_auto_schema(
        tags=["agent_sandbox"], request_body=SandboxExecInputSLZ(), responses={200: SandboxProcessOutputSLZ()}
    )
    def exec(self, request, sandbox_id):
        """在 Agent Sandbox 内执行命令。"""
        sandbox = self.get_sandbox_with_perm(request, sandbox_id)
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
        except SandboxExecTimeout:
            raise error_codes.AGENT_SANDBOX_PROCESS_EXEC_TIMEOUT.f(
                _("超时时间: {timeout}s").format(timeout=data["timeout"])
            )
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
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
        sandbox = self.get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxCodeRunInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            result = get_sandbox_client(sandbox).code_run(content=data["content"], language=data["language"])
        except SandboxExecTimeout:
            raise error_codes.AGENT_SANDBOX_PROCESS_EXEC_TIMEOUT
        except SandboxServiceNotReady:
            raise error_codes.AGENT_SANDBOX_SERVICE_NOT_READY
        except SandboxError:
            logger.exception("Failed to run code in sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_PROCESS_OPERATION_FAILED
        return Response(SandboxProcessOutputSLZ(result).data)

    @swagger_auto_schema(
        tags=["agent_sandbox"], query_serializer=SandboxGetLogsInputSLZ(), responses={200: SandboxGetLogsOutputSLZ()}
    )
    def logs(self, request, sandbox_id):
        """读取 Agent Sandbox 日志。"""
        sandbox = self.get_sandbox_with_perm(request, sandbox_id)
        slz = SandboxGetLogsInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            logs = get_sandbox_client(sandbox).get_logs(
                tail_lines=data.get("tail_lines"),
                timestamps=data["timestamps"],
            )
        except SandboxExecTimeout:
            raise error_codes.AGENT_SANDBOX_PROCESS_EXEC_TIMEOUT
        except SandboxError:
            logger.exception("Failed to get logs from sandbox: %s", sandbox.uuid)
            raise error_codes.AGENT_SANDBOX_PROCESS_OPERATION_FAILED
        return Response(SandboxGetLogsOutputSLZ({"logs": logs}).data)


@ForceAllowAuthedApp.mark_view_set
class AgentSandboxAPIPermissionViewSet(viewsets.ViewSet):
    """Agent Sandbox API 权限管理相关接口。

    AIDev 平台通过该接口为指定的 AI Agent 应用授予 Agent Sandbox 相关 API 的调用权限。
    授权完成后，该应用即可通过开发者中心提供的网关接口，访问沙箱的创建、删除、文件操作、进程管理及日志查看等接口。
    """

    permission_classes = [sysapi_client_perm_class(ClientAction.GRANT_APIGW_PERMISSIONS)]

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        request_body=GrantAgentSandboxPermissionSLZ(),
        responses={status.HTTP_201_CREATED: ""},
    )
    def grant_permissions(self, request):
        """为指定的 AI Agent 应用授予 Agent Sandbox 相关 API 的调用权限。"""
        slz = GrantAgentSandboxPermissionSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        target_app_code = validated_data["target_app_code"]
        expire_days = validated_data["expire_days"]

        tenant_id = get_tenant_id_for_app(target_app_code)
        try:
            client = ApiGatewayClient(tenant_id=tenant_id)
            client.grant_apigw_permissions(
                gateway_name=settings.APIGW_GRANT_GATEWAY_NAME,
                target_app_code=target_app_code,
                resource_names=settings.APIGW_GRANT_AGENT_SANDBOX_APIS,
                expire_days=expire_days,
            )
        except ApiGatewayServiceError as e:
            raise error_codes.REMOTE_REQUEST_ERROR.f(str(e))

        return Response(status=status.HTTP_201_CREATED)
