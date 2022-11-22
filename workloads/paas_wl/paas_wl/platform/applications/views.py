# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Any, Callable, Dict, List

from django.http import Http404, HttpRequest

from .exceptions import InstanceInPlaceNotFound
from .models import EngineApp
from .struct_models import Application, Module, ModuleEnv


class ApplicationCodeInPathMixin:
    """Provide some shortcuts to retrieve current application and do permission checks"""

    request: HttpRequest
    kwargs: Dict[str, Any]
    check_object_permissions: Callable

    def get_application(self) -> Application:
        """Return Application object according to current path kwargs.

        - required path vars: code or app_code
        """
        code = self._read_param_from_kwargs(['code', 'app_code'])
        try:
            application = self.request.insts_in_place.get_application_by_code(code)
        except InstanceInPlaceNotFound:
            raise Http404

        if not hasattr(self, 'check_object_permissions'):
            raise NotImplementedError("Only support the class which inherited from rest_framework.viewset")
        self.check_object_permissions(self.request, application)
        return application

    def get_module_via_path(self) -> Module:
        """Return Module object according to current path kwargs.

        - required path vars: module_name
        """
        # Get application object and do permission checks
        application = self.get_application()

        module_name = self._read_param_from_kwargs(['module_name'])
        try:
            # TODO: Support query from remote endpoint instead of read from local "instances-in-place"
            return self.request.insts_in_place.get_module_by_name(application, module_name)
        except InstanceInPlaceNotFound:
            raise Http404

    def get_module_env_via_path(self) -> ModuleEnv:
        """Return ModuleEnv object according to current path kwargs.

        - required path vars: module_name, environment
        """
        # Get application object and do permission checks
        application = self.get_application()

        module_name = self._read_param_from_kwargs(['module_name'])
        environment = self._read_param_from_kwargs(['environment'])
        try:
            # TODO: Support query from remote endpoint instead of read from local "instances-in-place"
            module = self.request.insts_in_place.get_module_by_name(application, module_name)
            return self.request.insts_in_place.get_module_env_by_environment(module, environment)
        except InstanceInPlaceNotFound:
            raise Http404

    def get_engine_app_via_path(self) -> EngineApp:
        """Return EngineAppPlain object according to current path kwargs.

        - required path vars: module_name, environment
        """
        # Get application object and do permission checks
        application = self.get_application()

        module_name = self._read_param_from_kwargs(['module_name'])
        environment = self._read_param_from_kwargs(['environment'])
        try:
            # TODO: Support query engine_app information from remote endpoint instead of read from
            # local "instances-in-place"
            obj = self.request.insts_in_place.query_engine_app(application.code, module_name, environment)
            return EngineApp.objects.get(name=obj.name)
        except InstanceInPlaceNotFound:
            raise Http404
        except EngineApp.DoesNotExist:
            raise Http404

    def _read_param_from_kwargs(self, names: List[str]):
        """Return the param value from self.kwargs, support multiple possible names

        :param names: List of possible parameter names
        :raises ValueError: When param can not be found
        """
        for param_name in names:
            try:
                return self.kwargs[param_name]
            except KeyError:
                continue
        raise ValueError(f'{names} not found in self.kwargs(path variables)')
