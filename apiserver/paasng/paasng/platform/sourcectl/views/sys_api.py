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

"""应用态 (系统 API) 视图

这些接口注册在 `sys/api/` 路径下, 仅供 AIDEV / AppSpark 等固定的系统调用, 鉴权依赖 sysapi_client.
"""

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.response import Response

from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.platform.applications.mixins import SysManagedAppInPathMixin
from paasng.platform.modules.models import Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.sourcectl import serializers as slzs
from paasng.utils.error_codes import error_codes

from .api import SourcePackageUploadViaUrlMixin, list_alternative_versions


class SysModuleSourcePackageViewSet(SourcePackageUploadViaUrlMixin, viewsets.ViewSet, SysManagedAppInPathMixin):
    """应用态源码包管理接口，AIDEV 为 AI Agent 应用、AppSpark 为 AppSpark 应用上传源码包。"""

    permission_classes = [sysapi_client_perm_class(ClientAction.UPLOAD_SOURCE_PACKAGE)]

    def get_module(self) -> Module:
        """获取目标模块，校验其所属应用归调用方管理，且模块使用源码包部署。"""
        module = self.get_managed_module_via_path()
        if not ModuleSpecs(module).deploy_via_package:
            raise error_codes.UNSUPPORTED_SOURCE_ORIGIN
        return module

    @swagger_auto_schema(
        request_body=slzs.SysSourcePackageUploadViaUrlSLZ,
        responses={200: slzs.SourcePackageSLZ()},
        tags=["源码包管理"],
        operation_description="提供给 AIDEV / AppSpark 使用的应用态上传源码包接口，只能操作调用方管理的应用",
    )
    def upload_via_url(self, request, code, module_name):
        """应用态根据 URL 上传源码包，AIDEV 只能操作 AI Agent 应用，AppSpark 只能操作 AppSpark 应用。"""
        module = self.get_module()
        slz = slzs.SysSourcePackageUploadViaUrlSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        operator = get_user_by_user_id(user_id_encoder.encode(settings.USER_TYPE, data["operator"]))
        source_package = self.do_upload_via_url(module, data, operator)
        return Response(data=slzs.SourcePackageSLZ(source_package).data)


class SysRepoDataViewSet(viewsets.ViewSet, SysManagedAppInPathMixin):
    """应用态源码分支接口, 目前仅支持 AIDEV 查询 AI Agent 应用的代码分支"""

    permission_classes = [sysapi_client_perm_class(ClientAction.READ_AI_AGENT_APP)]

    @swagger_auto_schema(tags=["应用/模块信息查询"], operation_id="sys_get_repo_branches")
    def get_repo_branches(self, request, code, module_name):
        """应用态获取蓝鲸应用的代码分支信息, 仅 AIDEV 可调用, 仅允许操作 AI Agent 应用"""
        module = self.get_managed_module_via_path()
        versions = list_alternative_versions(module, module.application, operator_user_id=module.owner)
        return Response({"results": versions})
