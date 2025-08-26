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
from typing import TYPE_CHECKING

from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN

from paas_wl.bk_app.applications.api import get_latest_build
from paas_wl.bk_app.processes.processes import ProcessManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paasng.accessories.serializers import DocumentaryLinkSLZ
from paasng.accessories.smart_advisor.advisor import DocumentaryLinkAdvisor
from paasng.accessories.smart_advisor.tags import get_dynamic_tag
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.accounts.permissions.user import user_has_feature
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.processes import serializers as slzs
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.platform.modules.specs import ModuleSpecs
from paasng.utils.error_codes import error_codes

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module

# Create your views here.

logger = logging.getLogger(__name__)


class ApplicationProcessWebConsoleViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def _is_whitelisted_user(self, request):
        return user_has_feature(AFF.ENABLE_WEB_CONSOLE)().has_permission(request, self)

    def _get_webconsole_docs_from_advisor(self):
        """从智能顾问中获取 web-console 相关的文档"""
        tag = get_dynamic_tag("app-feature:web-console")
        links = DocumentaryLinkAdvisor().search_by_tags([tag])
        if not links:
            # 如果数据库无文章记录, 就只能抛异常了
            raise error_codes.CANNOT_OPERATE_PROCESS.f(_("当前运行镜像不支持 WebConsole 功能，请尝试绑定最新运行时"))
        link = links[0]
        return DocumentaryLinkSLZ(link).data

    def _get_webconsole_command(self, module: "Module", runtime_type: str, is_cnb_runtime: bool):
        """获取进入 webconsole 的默认命令"""
        if runtime_type == RuntimeType.BUILDPACK:
            # cnb 运行时执行其他命令需要用 `launcher` 进入 buildpack 上下文
            # See: https://github.com/buildpacks/lifecycle/blob/main/cmd/launcher/cli/launcher.go
            if is_cnb_runtime:
                return "launcher bash"

            return "bash"

        # 如果不是 buildpack 构建类型，直接使用 sh 命令
        return "sh"

    @swagger_auto_schema(
        query_serializer=slzs.WebConsoleOpenSLZ, responses={200: slzs.WebConsoleResultSLZ}, tags=["获取控制台入口"]
    )
    def open(self, request, code, module_name, environment, process_type, process_instance_name):
        slz = slzs.WebConsoleOpenSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        # 必须调用 get_application() 方法才能触发权限校验
        app = self.get_application()
        module = self.get_module_via_path()
        env = self.get_env_via_path()
        manager = ProcessManager(env)

        runtime_type = ModuleSpecs(module).runtime_type
        is_cnb_runtime = False
        if runtime_type == RuntimeType.BUILDPACK:
            runtime_manager = ModuleRuntimeManager(module)
            is_encrypted_image = runtime_manager.is_secure_encrypted_runtime

            # 如果绑定的镜像未加密，则只有白名单中的用户才能访问
            if (not is_encrypted_image) and (not self._is_whitelisted_user(request)):
                docs = self._get_webconsole_docs_from_advisor()
                return Response(data=docs, status=HTTP_403_FORBIDDEN)

            if app.is_smart_app and (build := get_latest_build(env)):
                is_cnb_runtime = build.is_build_from_cnb()
            else:
                is_cnb_runtime = runtime_manager.is_cnb_runtime

        # 进入 WebConsole 的默认命令
        command = self._get_webconsole_command(module, runtime_type, is_cnb_runtime)
        try:
            result = manager.create_webconsole(
                request.user.username,
                process_type,
                process_instance_name,
                slz.validated_data.get("container_name"),
                command,
            )
        except AppEntityNotFound:
            raise error_codes.ERROR_UPDATING_PROC_SERVICE.f("未找到服务")

        data = result.get("data") or {}
        return Response(
            {
                "code": result.get("code"),
                "message": result.get("message"),
                "request_id": result.get("request_id"),
                "session_id": data.get("session_id"),
                "web_console_url": data.get("web_console_url"),
            }
        )
