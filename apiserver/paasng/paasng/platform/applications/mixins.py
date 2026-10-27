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

from typing import Any, Callable, Dict, List

from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from paas_wl.bk_app.applications.models import WlApp
from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.header import validate_tenant_id_header
from paasng.infras.accounts.permissions.application import BaseAppPermission
from paasng.infras.sysapi_client.constants import ClientRole
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.utils.error_codes import error_codes

from .models import Application, ModuleEnvironment


class ApplicationCodeInPathMixin:
    """
    Provide a shortcut to get current application and do permission checks
    """

    # To use this mixin, the subclass should set the `permission_classes` attribute and
    # use a application permission class, e.g.:
    #
    # permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    request: HttpRequest
    kwargs: Dict[str, Any]
    check_object_permissions: Callable
    get_permissions: Callable

    def get_application_without_perm(self):
        code = self._get_param_from_kwargs(["code", "app_code"])
        application = get_object_or_404(Application, code=code)
        return application

    def get_application(self) -> Application:
        """Return Application object according to current path kwargs.

        - required path vars: code or app_code
        """
        application = self.get_application_without_perm()
        if not hasattr(self, "check_object_permissions"):
            raise NotImplementedError("Only support the class which inherited from rest_framework.viewset")

        # raise an exception if current view class don't have any application permission classes
        # to prevent any potential security issues.
        if not any(isinstance(p, BaseAppPermission) for p in self.get_permissions()):
            raise ValueError("No application permission classes found in the view class.")

        self.check_object_permissions(self.request, application)
        return application

    def get_module_via_path(self) -> Module:
        """Return Module object according to current path kwargs.

        - required path vars: module_name
        """
        application = self.get_application()
        module_name = self._get_param_from_kwargs(["module_name"])
        try:
            return application.get_module(module_name)
        except Module.DoesNotExist:
            raise Http404

    def get_env_via_path(self) -> ModuleEnvironment:
        """Return ModuleEnvironment object according to current path kwargs.

        - required path vars: module_name, environment
        """
        application = self.get_application()
        module_name = self._get_param_from_kwargs(["module_name"])
        environment = self._get_param_from_kwargs(["environment"])

        try:
            module = application.get_module(module_name)
        except Module.DoesNotExist:
            raise Http404
        try:
            return module.get_envs(environment=environment)
        except ModuleEnvironment.DoesNotExist:
            raise Http404

    def get_engine_app_via_path(self) -> EngineApp:
        """Return EngineApp object according to current path kwargs.

        - required path vars: module_name, environment
        """
        return self.get_env_via_path().engine_app

    def get_wl_app_via_path(self) -> WlApp:
        """Return WlApp object according to current path kwargs.

        - required path vars: module_name, environment
        """
        return self.get_engine_app_via_path().to_wl_obj()

    def _get_param_from_kwargs(self, param_names: List[str]):
        """Return a param value from self.kwargs

        :raises ValueError: When param can not be found
        """
        for param_name in param_names:
            try:
                return self.kwargs[param_name]
            except KeyError:
                continue
        raise ValueError(f"{param_names} not found in self.kwargs(path variables)")


class SysManagedAppInPathMixin:
    """供应用态（系统 API）接口使用，根据路径参数获取调用方所管理应用下的模块/环境。

    不做任何用户维度的权限校验。动作权限由 sysapi 客户端权限类保证，这里只校验应用归属。
    """

    request: HttpRequest
    kwargs: Dict[str, Any]

    def get_managed_application_via_path(self) -> Application:
        """获取目标应用，其必须归当前调用方管理，且对请求头中的租户可用。

        - required path vars: code
        """
        application = get_object_or_404(Application, code=self.kwargs["code"])
        ensure_app_managed_by_client(application, self._get_client_role())

        # 全租户应用对所有租户可用
        if application.app_tenant_mode == AppTenantMode.GLOBAL.value:
            return application

        if application.app_tenant_id != validate_tenant_id_header(self.request):
            raise error_codes.APP_TENANT_MISMATCH
        return application

    def get_managed_module_via_path(self) -> Module:
        """获取目标模块，其所属应用必须归当前调用方管理。

        - required path vars: code, module_name
        """
        application = self.get_managed_application_via_path()

        try:
            module = application.get_module(self.kwargs.get("module_name"))
        except Module.DoesNotExist:
            raise Http404

        self._ensure_module_allowed_for_client(module)
        return module

    def ensure_env_managed_by_client(self, env: ModuleEnvironment) -> None:
        """校验环境归当前调用方管理，供路径里只有记录 ID、没有应用和模块的接口使用（如部署日志）。"""
        ensure_app_managed_by_client(env.application, self._get_client_role())
        self._ensure_module_allowed_for_client(env.module)
        self.ensure_env_allowed_for_client(env.environment)

    def get_managed_env_via_path(self) -> ModuleEnvironment:
        """获取目标环境，其所属应用必须归当前调用方管理，且环境在调用方允许的范围内。

        - required path vars: code, module_name, environment
        """
        module = self.get_managed_module_via_path()
        environment = self.kwargs["environment"]
        self.ensure_env_allowed_for_client(environment)

        try:
            return module.get_envs(environment=environment)
        except ModuleEnvironment.DoesNotExist:
            raise Http404

    def ensure_env_allowed_for_client(self, environment: str) -> None:
        """校验当前调用方可以操作该环境。

        路径里不带环境的接口（中断部署、查部署结果、部署日志、查下架结果）也要调用，按记录所在的环境校验。
        """
        # AppSpark 只发布到生产环境，预发布环境只留给用户在开发者中心手动部署
        if self._get_client_role() == ClientRole.APP_SPARK and environment != AppEnvironment.PRODUCTION:
            raise error_codes.SYSAPI_ENV_NOT_ALLOWED.f(_("仅支持操作生产环境"))

    def _ensure_module_allowed_for_client(self, module: Module) -> None:
        # AppSpark 只发布默认模块。用户在开发者中心新增的模块不是 AppSpark 打包的，不能经它部署或下架
        if self._get_client_role() == ClientRole.APP_SPARK and not module.is_default:
            raise error_codes.APP_SPARK_MODULE_REQUIRED

    def _get_client_role(self) -> ClientRole:
        return ClientRole(self.request.sysapi_client.role)  # type: ignore[attr-defined]


def ensure_app_managed_by_client(application: Application, role: ClientRole) -> None:
    """校验应用归调用方管理：AIDEV 只能操作 AI Agent 应用，AppSpark 只能操作默认模块来源仍为 AppSpark 的应用。

    :raises APIError: 应用不归调用方管理
    """
    if role == ClientRole.AIDEV:
        if not application.is_ai_agent_app:
            raise error_codes.AI_AGENT_APP_REQUIRED
        return

    if role == ClientRole.APP_SPARK:
        # 用户在开发者中心把来源切换为代码仓库后，应用就脱离 AppSpark 管理
        if application.get_default_module().get_source_origin() != SourceOrigin.APP_SPARK:
            raise error_codes.APP_SPARK_APP_REQUIRED
        return

    # 给其它角色发了这批动作权限却没写归属规则时，宁可拒绝也不放行任意应用
    raise error_codes.SYSAPI_CLIENT_PERM_DENIED
