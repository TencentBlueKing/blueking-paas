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

from django.http import JsonResponse
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.tools.build_smart.models import SmartBuildRecord
from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.exceptions import PreparedPackageNotFound
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.prepared import PreparedSourcePackage
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.utils.error_codes import error_codes
from paasng.utils.views import get_filepath

from .coordinator import SmartBuildCoordinator
from .exceptions import SmartBuildInterruptionFailed
from .interruptions import interrupt_smart_build
from .serializers import (
    SmartBuildInputSLZ,
    SmartBuildOutputSLZ,
    ToolPackageStashInputSLZ,
    ToolPackageStashOutputSLZ,
)
from .task import SmartBuildTaskRunner, initialize_smart_build_record

logger = logging.getLogger(__name__)


class SmartBuilderViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

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

    @swagger_auto_schema(request_body=SmartBuildInputSLZ, responses={"201": SmartBuildOutputSLZ()})
    def build_smart(self, request):
        """根据暂存的源码包构建 s-mart 包"""
        slz = SmartBuildInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        app_code = slz.validated_data["app_code"]
        signature = slz.validated_data["signature"]

        # 1. 根据 app_code 找到之前上传的源码包, 将其下载到临时目录
        with generate_temp_dir() as tmp_dir:
            try:
                package_path = PreparedSourcePackage(
                    request,
                    namespace=self._get_store_namespace(app_code),
                ).retrieve(tmp_dir)
            except PreparedPackageNotFound:
                logger.exception(f"Failed to retrieve prepared package for app: {app_code}")
                raise error_codes.PACKAGE_NOT_FOUND.f(_("源码包不存在或已过期"))

            # 2. 校验下载文件的 signature
            stat = SourcePackageStatReader(package_path).read()
            if stat.sha256_signature != signature:
                logger.error(
                    "the provided digital signature is inconsistent with "
                    "the digital signature of the actually saved source code package."
                )
                raise error_codes.FILE_CORRUPTED_ERROR.f(_("文件签名不一致"))

        # 3. 保证同一时间构建的唯一性
        # 使用文件的数字签名来决定构建任务的唯一标识
        coordinator = SmartBuildCoordinator(signature)
        if not coordinator.acquire_lock():
            raise error_codes.CANNOT_BUILD_ONGOING_EXISTS.f(_("正在构建 s-mart 包, 请勿重复提交构建"))

        smart_build_id = ""
        with coordinator.release_on_error():
            smart_build = initialize_smart_build_record(
                package_path=package_path,
                signature=signature,
                operator=request.user.pk,
            )
            smart_build_id = smart_build.id
            coordinator.set_smart_build(smart_build)
            # Start a background s-mart build task
            SmartBuildTaskRunner(smart_build, package_path).start()
        return JsonResponse(
            data={"smart_build_id": smart_build_id, "stream_url": f"/streams/{smart_build_id}"},
            status=status.HTTP_201_CREATED,
        )

    def user_interrupt(self, request, build_id):
        """由用户手动中断 s-mart 包构建"""
        try:
            smart_build_record = SmartBuildRecord.objects.get(id=build_id)
            interrupt_smart_build(smart_build_record, request.user)
        except SmartBuildRecord.DoesNotExist:
            raise error_codes.NOT_FOUND_SMART_BUILD_RECORD.f(
                _("没有 id 为 {build_id} s-mart 包构建记录").format(build_id=build_id)
            )
        except SmartBuildInterruptionFailed as e:
            raise error_codes.BUILD_INTERRUPTION_FAILED.f(str(e))
        return Response({})

    @staticmethod
    def _validate_app_desc(app_desc: ApplicationDesc):
        # TODO 增加一些前置校验, 确保 app_desc 符合构建要求
        if app_desc.market is None:
            raise DescriptionValidationError({"market": "内容不能为空"})

    @staticmethod
    def _get_store_namespace(app_code: str) -> str:
        return f"{app_code}:prepared_build"
