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

import copy
import logging
import tarfile
from os import PathLike
from pathlib import Path
from typing import List, cast

from blue_krill.storages.blobstore.exceptions import DownloadFailedError, UploadFailedError
from django.db.transaction import atomic
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from moby_distribution.registry.exceptions import RequestError as RequestRegistryError
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.publish.sync_market.utils import cascade_delete_legacy_app
from paasng.accessories.servicehub.exceptions import BindServicePlanError
from paasng.accessories.servicehub.manager import ServiceObj, mixed_service_mgr
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application, SMartAppExtraInfo
from paasng.platform.applications.tenant import validate_app_tenant_params
from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.exceptions import GenAppCodeError, PreparedPackageNotFound
from paasng.platform.smart_app.serializers import (
    AppDescriptionSLZ,
    PackageStashConfirmRequestSLZ,
    PackageStashRequestSLZ,
    PackageStashResponseSLZ,
)
from paasng.platform.smart_app.services.app_desc import gen_app_code_when_conflict, get_app_description
from paasng.platform.smart_app.services.detector import SourcePackageStatReader, update_meta_info
from paasng.platform.smart_app.services.dispatch import dispatch_package_to_modules
from paasng.platform.smart_app.services.prepared import PreparedSourcePackage
from paasng.platform.sourcectl.models import SourcePackage
from paasng.platform.sourcectl.package.downloader import download_package
from paasng.platform.sourcectl.serializers import SourcePackageSLZ
from paasng.platform.sourcectl.utils import generate_temp_dir, generate_temp_file
from paasng.utils.error_codes import error_codes
from paasng.utils.views import get_filepath

logger = logging.getLogger(__name__)


class SMartPackageCreatorViewSet(viewsets.ViewSet):
    """上传与管理 S-Mart 应用市场规则的源码包，可通过源码包直接创建应用"""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    def handle_exception(self, exc):
        if isinstance(exc, (DownloadFailedError, UploadFailedError)):
            raise error_codes.OBJECT_STORE_EXCEPTION.f(_("请联系管理员")) from exc
        return super().handle_exception(exc)

    @swagger_auto_schema(
        request_body=PackageStashRequestSLZ,
        response_serializer=PackageStashResponseSLZ,
        tags=["S-Mart", "创建应用"],
    )
    def upload(self, request):
        """上传一个 S-Mart 源码包，并将其暂存起来"""
        if not AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_CREATE_SMART_APP):
            raise ValidationError(_("你无法创建 SMart 应用"))

        slz = PackageStashRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        package_fp = slz.validated_data["package"]

        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(
            request.user, slz.validated_data["app_tenant_mode"]
        )

        with generate_temp_dir() as download_dir:
            filepath = get_filepath(package_fp, str(download_dir))

            stat = SourcePackageStatReader(filepath).read()

            original_app_desc = get_app_description(stat)
            app_desc = self.validate_and_prepare_app_desc(original_app_desc, app_tenant_id)

            if not stat.version:
                raise error_codes.MISSING_VERSION_INFO

            # Store as prepared package for later usage(create_prepared)
            PreparedSourcePackage(request).store(filepath)

        logger.debug("[S-Mart] fetching remote services by region.")
        supported_services = list(mixed_service_mgr.list_visible())
        supported_services = cast(List[ServiceObj], supported_services)

        return Response(
            data=PackageStashResponseSLZ(
                {
                    "app_description": app_desc,
                    "signature": stat.sha256_signature,
                    "supported_services": [service.name for service in supported_services],
                    "original_app_description": original_app_desc,
                }
            ).data
        )

    @swagger_auto_schema(request_body=PackageStashConfirmRequestSLZ, tags=["S-Mart", "创建应用"])
    def confirm(self, request):
        """根据已暂存的 S-Mart 源码包创建应用"""
        if not AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_CREATE_SMART_APP):
            raise ValidationError(_("你无法创建 S-Mart 应用"))

        slz = PackageStashConfirmRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(
            request.user, slz.validated_data["app_tenant_mode"]
        )

        with generate_temp_dir() as download_dir:
            # Step 1. retrieve package(tarball)
            try:
                filepath = PreparedSourcePackage(request).retrieve(download_dir)
            except PreparedPackageNotFound:
                logger.exception("S-Mart package does not exist!")
                raise error_codes.PREPARED_PACKAGE_NOT_FOUND

            if not self.is_valid_tar_file(filepath):
                raise error_codes.FILE_CORRUPTED_ERROR.f(_("源码文件加载不完整，请重试或联系管理员"))

            # Step 2. create application, module
            stat = SourcePackageStatReader(filepath).read()
            if not stat.version:
                raise error_codes.MISSING_VERSION_INFO

            original_app_desc = get_app_description(stat)

            # 替换成实际待创建的应用信息
            stat.meta_info = update_meta_info(
                stat.meta_info,
                app_code=slz.validated_data["code"],
                app_name=slz.validated_data["name_zh_cn"],
            )
            # 租户信息放到单独的字段中，不会干扰应用描述文件字段
            stat.meta_info["tenant"] = {
                "app_tenant_mode": app_tenant_mode,
                "app_tenant_id": app_tenant_id,
                "tenant_id": tenant.id,
            }

            handler = get_desc_handler(stat.meta_info)
            with atomic():
                # 由于创建应用需要操作 v2 的数据库, 因此将事务的粒度控制在 handle_app 的维度, 避免其他地方失败导致创建应用的操作回滚, 但是 v2 中 app code 已被占用的问题.
                try:
                    application = handler.handle_app(request.user)
                except (ControllerError, DescriptionValidationError, BindServicePlanError) as e:
                    # 清理 v2 中创建的应用
                    cascade_delete_legacy_app("code", application.code, False)
                    logger.exception("Create app error !")
                    raise error_codes.FAILED_TO_HANDLE_APP_DESC.f(e.message)
                else:
                    # 创建 SMartAppExtraInfo, 记录应用原始 code
                    SMartAppExtraInfo.objects.create(
                        app=application, original_code=original_app_desc.code, tenant_id=application.tenant_id
                    )

            # Step 3. dispatch package as Image to registry
            try:
                with atomic():
                    dispatch_package_to_modules(
                        application,
                        tarball_filepath=filepath,
                        stat=stat,
                        operator=request.user,
                        modules=set(handler.app_desc.modules.keys()),
                    )
            except DescriptionValidationError as e:
                logger.exception("Handling S-Mart Package Exceptions!")
                raise error_codes.FAILED_TO_HANDLE_APP_DESC.f(e.message)
            except RequestRegistryError as e:
                logger.exception("Failed to access container registry!")
                raise error_codes.FAILED_TO_PUSH_IMAGE.f(e.message)
        return Response({}, status=status.HTTP_201_CREATED)

    @staticmethod
    def validate_and_prepare_app_desc(original_app_desc: ApplicationDesc, app_tenant_id: str) -> ApplicationDesc:
        """validate original app_desc and prepare app_desc which will be used to create app"""
        if original_app_desc.market is None:
            raise ValidationError(_("缺失应用市场配置（market)!"))

        if not original_app_desc.instance_existed:
            return original_app_desc

        try:
            smart_app = SMartAppExtraInfo.objects.get(
                original_code=original_app_desc.code, app__app_tenant_id=app_tenant_id
            )
        except SMartAppExtraInfo.DoesNotExist:
            # 生成可创建应用的 app_desc. 其中, code 随机生成, 保证唯一性, 用于前端推荐值
            app_desc = copy.deepcopy(original_app_desc)
            app_desc.instance_existed = False
            try:
                app_desc.code = gen_app_code_when_conflict(original_app_desc.code)
            except GenAppCodeError:
                raise error_codes.PREPARED_PACKAGE_ERROR.f(_("自动生成应用 ID 失败，请重试或联系管理员"))
            else:
                return app_desc
        else:
            raise ValidationError(
                _("S-mart 包已用于创建应用（ID：{smart_app_code}），不允许重复创建!").format(
                    smart_app_code=smart_app.app.code
                )
            )

    @staticmethod
    def is_valid_tar_file(filepath: PathLike) -> bool:
        """检查指定路径的文件是否为 tar 包"""
        try:
            with tarfile.open(Path(filepath), "r"):
                return True
        except tarfile.TarError:
            return False


@method_decorator(name="list", decorator=swagger_auto_schema(tags=["源码包管理", "S-Mart"]))
class SMartPackageManagerViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin, viewsets.mixins.ListModelMixin):
    """管理某个 S-Mart 应用的源码包"""

    serializer_class = SourcePackageSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    search_fields = ["version", "package_name", "package_size"]
    ordering = ("-created",)
    ordering_fields = ("version", "package_name", "package_size", "updated")
    parser_classes = [MultiPartParser, JSONParser]

    def get_queryset(self):
        return self.get_application().get_default_module().packages.all()

    def handle_exception(self, exc):
        if isinstance(exc, (DownloadFailedError, UploadFailedError)):
            raise error_codes.OBJECT_STORE_EXCEPTION.f(_("请联系管理员")) from exc
        return super().handle_exception(exc)

    @swagger_auto_schema(tags=["源码包管理", "S-Mart"], response_serializer=AppDescriptionSLZ)
    def retrieve(self, request, code, pk):
        # 前端目前未调用该接口, 考虑移除或限制 s-mart 应用调用.
        application = self.get_application()
        package = get_object_or_404(SourcePackage, pk=pk)

        if not application.modules.filter(id=package.module_id).exists():
            raise Http404("Package Not Found.")

        with generate_temp_file() as file_path:
            download_package(package, dest_path=file_path)
            stat = SourcePackageStatReader(file_path).read()
            app_desc = get_app_description(stat)
        return Response(data=AppDescriptionSLZ(app_desc).data)

    @staticmethod
    def validate_and_prepare_app_desc(original_app_desc: ApplicationDesc, app: Application) -> ApplicationDesc:
        """validate original app_desc and prepare app_desc which will be used to update app"""
        if original_app_desc.spec_version == AppSpecVersion.VER_3 and app.type != ApplicationType.CLOUD_NATIVE:
            raise ValidationError(_("非云原生应用, 请使用 (spec_version: 2) 版本的应用描述文件"))

        if original_app_desc.market is None:
            raise ValidationError(_("缺失应用市场配置（market)!"))

        if not SMartAppExtraInfo.objects.filter(original_code=original_app_desc.code, app=app).exists():
            raise ValidationError(
                _("应用描述文件中声明的应用 ID({app_desc_code}) 未创建过 S-mart 应用").format(
                    app_desc_code=original_app_desc.code
                )
            )

        # 准备可更新应用的 app_desc. 其中, code 设置为实际待更新的 app code
        app_desc = copy.deepcopy(original_app_desc)
        app_desc.code = app.code
        app_desc.name_zh_cn = app.name
        app_desc.instance_existed = True
        return app_desc

    @swagger_auto_schema(
        tags=["源码包管理", "S-Mart"],
        request_body=PackageStashRequestSLZ,
        response_serializer=PackageStashResponseSLZ,
        parser_classes=[MultiPartParser],
    )
    def stash(self, request, code):
        """上传一个源码包，并将其暂存起来, 并返回 diff"""
        application = self.get_application()
        namespace = f"{application.code}"

        slz = PackageStashRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        package_fp = slz.validated_data["package"]

        with generate_temp_dir() as download_dir:
            filepath = get_filepath(package_fp, download_dir)

            stat = SourcePackageStatReader(filepath).read()

            original_app_description = get_app_description(stat)
            app_desc = self.validate_and_prepare_app_desc(original_app_description, application)

            if not stat.version:
                raise error_codes.MISSING_VERSION_INFO

            # Store as prepared package for later usage(commit)
            PreparedSourcePackage(request, namespace=namespace).store(filepath)

        supported_services = mixed_service_mgr.list_visible()
        return Response(
            data=PackageStashResponseSLZ(
                {
                    "app_description": app_desc,
                    "signature": stat.sha256_signature,
                    "supported_services": [service.name for service in supported_services],
                    "original_app_description": original_app_description,
                }
            ).data
        )

    @atomic
    @swagger_auto_schema(tags=["源码包管理", "S-Mart"])
    def commit(self, request, code, signature):
        """保存暂存的源码包, 并应用源码包内的应用描述信息."""
        application = self.get_application()

        with generate_temp_dir() as download_dir:
            # Step 1. retrieve package(tarball)
            try:
                filepath = PreparedSourcePackage(request).retrieve(download_dir)
            except PreparedPackageNotFound:
                logger.exception("S-Mart package does not exist！")
                raise error_codes.PREPARED_PACKAGE_NOT_FOUND

            stat = SourcePackageStatReader(filepath).read()
            if stat.sha256_signature != signature:
                logger.error(
                    "the provided digital signature is inconsistent with "
                    "the digital signature of the actually saved source code package."
                )
                raise error_codes.FILE_CORRUPTED_ERROR.f(_("文件签名不一致"))
            if not stat.version:
                raise error_codes.MISSING_VERSION_INFO

            # Step 2. handle app(create module if necessary)
            # 替换成实际待更新的应用信息
            stat.meta_info = update_meta_info(
                stat.meta_info,
                app_code=application.code,
                app_name=application.name,
            )
            # 租户信息放到单独的字段中，不会干扰应用描述文件字段
            stat.meta_info["tenant"] = {
                "app_tenant_mode": application.app_tenant_mode,
                "app_tenant_id": application.app_tenant_id,
                "tenant_id": application.tenant_id,
            }
            handler = get_desc_handler(stat.meta_info)
            try:
                application = handler.handle_app(request.user)
            except (ControllerError, DescriptionValidationError) as e:
                logger.exception("Failed to update app info！")
                raise error_codes.FAILED_TO_HANDLE_APP_DESC.f(e.message)

            # Step 3. patch package, store it and bind to module.
            try:
                dispatch_package_to_modules(
                    application,
                    tarball_filepath=filepath,
                    stat=stat,
                    operator=request.user,
                    modules=set(handler.app_desc.modules.keys()),
                )
            except DescriptionValidationError as e:
                logger.exception("Handling S-Mart Package Exceptions!")
                raise error_codes.FAILED_TO_HANDLE_APP_DESC.f(e.message)
            except RequestRegistryError as e:
                logger.exception("Failed to access container registry!")
                raise error_codes.FAILED_TO_PUSH_IMAGE.f(e.message)
        return Response(status=status.HTTP_201_CREATED)
