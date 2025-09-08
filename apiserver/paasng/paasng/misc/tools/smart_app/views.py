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
from paasng.misc.tools.smart_app.build import (
    SmartBuildCoordinator,
    SmartBuildTaskRunner,
    create_smart_build_record,
)
from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from paasng.misc.tools.smart_app.phases_steps import ALL_STEP_METAS, SmartBuildPhaseManager, get_sorted_steps
from paasng.misc.tools.smart_app.serializers import (
    SmartBuildFramePhaseSLZ,
    SmartBuildInputSLZ,
    SmartBuildOutputSLZ,
    SmartBuildPhaseSLZ,
    ToolPackageStashInputSLZ,
    ToolPackageStashOutputSLZ,
)
from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.exceptions import PreparedPackageNotFound
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.prepared import PreparedSourcePackage
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.utils.error_codes import error_codes
from paasng.utils.views import get_filepath

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

    @swagger_auto_schema(
        request_body=SmartBuildInputSLZ,
        responses={"201": SmartBuildOutputSLZ()},
        tags=["S-Mart 包构建"],
    )
    def build_smart(self, request):
        """根据暂存的源码包构建 s-mart 包"""
        slz = SmartBuildInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        app_code = slz.validated_data["app_code"]
        signature = slz.validated_data["signature"]

        prepared_package = PreparedSourcePackage(request, namespace=self._get_store_namespace(app_code))

        with generate_temp_dir() as tmp_dir:
            try:
                package_path = prepared_package.retrieve(tmp_dir)
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

        # 使用 operator 和 app_code 组合构建锁, 避免重复构建
        coordinator = SmartBuildCoordinator(f"{request.user.pk}:{app_code}")
        if not coordinator.acquire_lock():
            raise error_codes.CANNOT_BUILD_ONGOING_EXISTS.f(_("正在构建 s-mart 包, 请勿重复提交构建"))

        with coordinator.release_on_error():
            store_url, filename = prepared_package.get_stored_info()
            smart_build = create_smart_build_record(
                package_name=filename,
                app_code=app_code,
                operator=request.user.pk,
            )
            build_id = smart_build.uuid
            coordinator.set_smart_build(smart_build)
            # Start a background deploy task
            SmartBuildTaskRunner(smart_build, store_url, package_path).start()
        return JsonResponse(
            data={"build_id": build_id, "stream_url": f"/streams/{build_id}"},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _validate_app_desc(app_desc: ApplicationDesc):
        # TODO 增加一些前置校验, 确保 app_desc 符合构建要求
        if app_desc.market is None:
            raise DescriptionValidationError({"market": "内容不能为空"})

    @staticmethod
    def _get_store_namespace(app_code: str) -> str:
        return f"{app_code}:prepared_build"


class SmartBuildPhaseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(tags=["S-Mart 包构建"], responses={"200": SmartBuildFramePhaseSLZ(many=True)})
    def get_frame(self):
        """获取 S-mart 包构建的阶段和步骤信息"""
        phases = []
        for phase_type in SmartBuildPhaseType:
            # 从 ALL_STEP_METAS 过滤出属于当前 phase 的步骤并按 name 排序
            phase_steps = sorted(
                (s for s in ALL_STEP_METAS.values() if s.phase == phase_type.value),
                key=lambda s: s.name,
            )
            phases.append({"type": phase_type.value, "_sorted_steps": phase_steps})

        return Response(data=SmartBuildFramePhaseSLZ(phases, many=True).data)

    @swagger_auto_schema(tags=["S-Mart 包构建"], responses={"200": SmartBuildPhaseSLZ(many=True)})
    def get_result(self, request, smart_build_id: str):
        try:
            smart_build = SmartBuildRecord.objects.get(pk=smart_build_id)
        except SmartBuildRecord.DoesNotExist:
            raise error_codes.NOT_FOUND_SMART_BUILD

        manager = SmartBuildPhaseManager(smart_build)
        try:
            phases = [smart_build.phases.get(type=phase_type) for phase_type in manager.list_phase_types()]
        except Exception:
            logger.exception("failed to get phase info")
            raise error_codes.CANNOT_GET_SMART_BUILD_PHASES

        # Set property for rendering by slz
        for p in phases:
            p._sorted_steps = get_sorted_steps(p)
        return Response(data=SmartBuildPhaseSLZ(phases, many=True).data)
