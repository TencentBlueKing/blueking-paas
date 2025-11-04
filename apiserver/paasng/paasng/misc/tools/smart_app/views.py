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

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.utils.blobstore import make_blob_store
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.engine.constants import JobStatus
from paasng.platform.smart_app.exceptions import PreparedPackageNotFound
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.prepared import PreparedSourcePackage
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.utils.error_codes import error_codes
from paasng.utils.views import get_filepath

from .build import SmartBuildCoordinator, SmartBuildTaskRunner, create_smart_build_record
from .filters import SmartBuildRecordFilterBackend
from .models import SmartBuildRecord
from .output import get_all_logs
from .serializers import (
    SmartBuildHistoryLogsOutputSLZ,
    SmartBuildHistoryOutputSLZ,
    SmartBuildInputSLZ,
    SmartBuildOutputSLZ,
    ToolPackageStashInputSLZ,
    ToolPackageStashOutputSLZ,
)

logger = logging.getLogger(__name__)


class SmartBuilderViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    queryset = SmartBuildRecord.objects.all()
    filter_backends = [SmartBuildRecordFilterBackend]
    pagination_class = LimitOffsetPagination

    @swagger_auto_schema(
        request_body=ToolPackageStashInputSLZ,
        response_serializer=ToolPackageStashOutputSLZ,
        tags=["S-Mart 包构建"],
    )
    def upload(self, request):
        """上传一个待构建的源码包，校验通过后将其暂存起来"""
        slz = ToolPackageStashInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        with generate_temp_dir() as tmp_dir:
            filepath = get_filepath(slz.validated_data["package"], str(tmp_dir))
            stat = SourcePackageStatReader(filepath).read()

            if not stat.meta_info:
                raise error_codes.MISSING_DESCRIPTION_INFO.f(_("解压后未找到 app_desc.yaml 文件"))

            if stat.relative_path != "./":
                raise error_codes.MISSING_DESCRIPTION_INFO.f(_("解压后未在根目录下找到 app_desc.yaml 文件"))

            try:
                app_desc = get_desc_handler(stat.meta_info).app_desc
                self._validate_app_desc(app_desc)
            except DescriptionValidationError as e:
                raise error_codes.FAILED_TO_HANDLE_APP_DESC.f(str(e))

            if not stat.version:
                raise error_codes.MISSING_VERSION_INFO.f(_("app_desc.yaml 中缺少了 app version 信息"))

            # Store as prepared package for later build
            PreparedSourcePackage(request, namespace=self._get_store_namespace(app_desc.code)).store(filepath)

        return Response(
            ToolPackageStashOutputSLZ(
                {"app_code": app_desc.code, "signature": stat.sha256_signature},
            ).data
        )

    @swagger_auto_schema(
        request_body=SmartBuildInputSLZ,
        responses={status.HTTP_201_CREATED: SmartBuildOutputSLZ()},
        tags=["S-Mart 包构建"],
    )
    def build_smart(self, request):
        """启动构建任务"""

        slz = SmartBuildInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        app_code = slz.validated_data["app_code"]
        signature = slz.validated_data["signature"]

        prepared_package = PreparedSourcePackage(request, namespace=self._get_store_namespace(app_code))

        with generate_temp_dir() as tmp_dir:
            try:
                package_path = prepared_package.retrieve(tmp_dir)
            except PreparedPackageNotFound:
                raise error_codes.PACKAGE_NOT_FOUND.f(_("源码包不存在或已过期"))

            stat = SourcePackageStatReader(package_path).read()
            if stat.sha256_signature != signature:
                raise error_codes.FILE_CORRUPTED_ERROR.f(_("文件签名不一致"))

        # 获取构建锁
        coordinator = SmartBuildCoordinator(f"{request.user.pk}:{app_code}")
        if not coordinator.acquire_lock():
            raise error_codes.CANNOT_BUILD_ONGOING_EXISTS.f(_("正在构建中，请勿重复提交"))

        with coordinator.release_on_error():
            store_url, filename = prepared_package.get_stored_info()
            smart_build = create_smart_build_record(
                package_name=filename,
                app_code=app_code,
                app_version=stat.version,
                sha256_signature=stat.sha256_signature,
                operator=request.user.pk,
            )
            coordinator.set_smart_build(smart_build)
            # Start a background deploy task
            SmartBuildTaskRunner(
                smart_build_id=smart_build.uuid,
                source_url=store_url,
                app_code=app_code,
                app_version=stat.version,
                sha256_signature=stat.sha256_signature,
            ).start()

        data = {"build_id": str(smart_build.uuid), "stream_url": f"/streams/{smart_build.uuid}"}
        return JsonResponse(data=SmartBuildOutputSLZ(data).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["S-Mart 包构建"],
        operation_description="获取构建历史",
        responses={status.HTTP_200_OK: SmartBuildHistoryOutputSLZ(many=True)},
    )
    def list_history(self, request):
        """获取构建历史列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        slz = SmartBuildHistoryOutputSLZ(page, many=True)
        return self.get_paginated_response(slz.data)

    @swagger_auto_schema(
        tags=["S-Mart 包构建"],
        operation_description="获取构建日志",
        responses={status.HTTP_200_OK: SmartBuildHistoryLogsOutputSLZ()},
    )
    def get_history_logs(self, request, uuid: str):
        """获取构建日志"""
        record = get_object_or_404(SmartBuildRecord, uuid=uuid, operator=request.user)
        logs = get_all_logs(record)
        result = {
            "status": record.status,
            "start_time": record.start_time,
            "end_time": record.end_time,
            "logs": logs,
        }
        return JsonResponse(SmartBuildHistoryLogsOutputSLZ(result).data)

    def download_history_logs(self, request, uuid: str):
        """下载构建日志"""
        smart_build_record = get_object_or_404(SmartBuildRecord, uuid=uuid, operator=request.user)
        logs = get_all_logs(smart_build_record)
        filename = f"{smart_build_record.package_name}-{uuid}.log"

        response = HttpResponse(logs, content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    def download_artifact(self, request, uuid: str):
        """下载构建产物"""
        record = get_object_or_404(SmartBuildRecord, uuid=uuid, operator=request.user)

        if record.status != JobStatus.SUCCESSFUL:
            raise error_codes.ARTIFACT_NOT_FOUND.f(_("构建未成功，无法下载构建产物"))

        artifact_url = record.artifact_url
        if not artifact_url or not artifact_url.startswith("blobstore://"):
            raise error_codes.ARTIFACT_NOT_FOUND.f("制品不存在")

        # 移除 blobstore:// 前缀并解析
        artifact_path = record.artifact_url.replace("blobstore://", "")
        bucket, key = artifact_path.split("/", 1)

        # 生成临时下载链接
        store = make_blob_store(bucket)
        download_url = store.generate_presigned_url(key=key, expires_in=3600)

        return Response(data={"download_url": download_url})

    @staticmethod
    def _validate_app_desc(app_desc: ApplicationDesc):
        """校验应用描述文件"""
        if app_desc.market is None:
            raise DescriptionValidationError({"market": "内容不能为空"})

    @staticmethod
    def _get_store_namespace(app_code: str) -> str:
        return f"{app_code}:prepared_build"
