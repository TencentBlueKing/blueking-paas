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

from paas_wl.bk_app.applications.models import WlApp
from paasng.infras.accounts.permissions.application import BaseAppPermission
from paasng.platform.engine.models import EngineApp
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


class AIAgentAppInPathMixin:
    """供应用态（系统 API）接口使用，根据路径参数获取 AI Agent 应用下的模块/环境。

    不做任何用户维度的权限校验，调用方需要通过 sysapi 客户端权限保证安全。
    """

    kwargs: Dict[str, Any]

    def get_ai_agent_module_via_path(self) -> Module:
        """获取目标模块，其所属应用必须是 AI Agent 应用。

        - required path vars: code, module_name
        """
        application = get_object_or_404(Application, code=self.kwargs["code"])
        if not application.is_ai_agent_app:
            raise error_codes.AI_AGENT_APP_REQUIRED

        try:
            return application.get_module(self.kwargs.get("module_name"))
        except Module.DoesNotExist:
            raise Http404

    def get_ai_agent_env_via_path(self) -> ModuleEnvironment:
        """获取目标环境，其所属应用必须是 AI Agent 应用。

        - required path vars: code, module_name, environment
        """
        module = self.get_ai_agent_module_via_path()
        try:
            return module.get_envs(environment=self.kwargs["environment"])
        except ModuleEnvironment.DoesNotExist:
            raise Http404
