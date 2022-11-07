# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
"""Preconditions for Modify Application/Module"""
from contextlib import contextmanager
from enum import Enum
from typing import Dict, List, Type

from django.utils.translation import gettext as _
from rest_framework import permissions

from paasng.platform.applications.models import Application
from paasng.platform.core.protections.base import BaseCondition, ProtectionStatus
from paasng.platform.core.protections.exceptions import ConditionNotMatched
from paasng.utils.error_codes import error_codes


class BaseAppResProtectCondition(BaseCondition):
    def __init__(self, application: Application):
        self.application = application

    def validate(self):
        raise NotImplementedError


class ProtectedRes(Enum):
    """Protected application resources, it is usually a virtual "resource" and have no corresponding data"""

    BASIC_INFO_MODIFICATIONS = 'BASIC_INFO_MODIFICATIONS'
    SERVICES_MODIFICATIONS = 'SERVICES_MODIFICATIONS'
    DISABLE_APP_DESC = 'DISABLE_APP_DESC'


class AppDescDisableProtectCondition(BaseAppResProtectCondition):
    action = "disable_application_description"

    def validate(self):
        if self.application.is_smart_app:
            raise ConditionNotMatched(_("S-Mart 不可关闭应用描述文件"), self.action)


class AppResProtector:
    """protects application's related resource"""

    _registed_preconditions: Dict[ProtectedRes, List[Type[BaseAppResProtectCondition]]] = {
        ProtectedRes.DISABLE_APP_DESC: [AppDescDisableProtectCondition]
    }

    def __init__(self, application: Application):
        self.application = application

    def list_status(self) -> Dict[ProtectedRes, ProtectionStatus]:
        """Return all protection statuses"""
        result = {}
        for res_type in ProtectedRes:
            result[res_type] = self.get_status(res_type)
        return result

    def get_status(self, res_type: ProtectedRes) -> ProtectionStatus:
        """Return the protection status of an app resource"""
        for condition_cls in self._registed_preconditions.get(res_type, []):
            try:
                condition_cls(self.application).validate()
            except ConditionNotMatched as e:
                return ProtectionStatus([e])
        return ProtectionStatus([])

    @classmethod
    def register_precondition(cls, res_type: ProtectedRes, precondition: Type[BaseAppResProtectCondition]):
        """Register new Preconditions"""
        preconditions = cls._registed_preconditions.setdefault(res_type, [])
        if precondition not in preconditions:
            preconditions.append(precondition)

    @classmethod
    @contextmanager
    def override_preconditions(cls, preconditions: Dict[ProtectedRes, List[Type[BaseAppResProtectCondition]]]):
        old = cls._registed_preconditions
        try:
            cls._registed_preconditions = preconditions
            yield
        finally:
            cls._registed_preconditions = old


def raise_if_protected(application: Application, res_type: ProtectedRes):
    """Raise error if app resource is protected

    :raises: ErrorCode
    """
    status = AppResProtector(application).get_status(res_type)
    if status.activated:
        raise error_codes.APP_RES_PROTECTED.f(status.reason)


def res_must_not_be_protected_perm(res_type: ProtectedRes) -> Type[permissions.BasePermission]:
    """Check if application's resource was protected"""

    class Permission(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            raise_if_protected(obj, res_type)
            return True

    return Permission
