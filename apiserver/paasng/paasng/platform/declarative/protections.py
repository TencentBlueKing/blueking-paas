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

"""Protect resources created by declarative configs from external modifications"""
from django.utils.translation import gettext_lazy as _

from paasng.core.core.protections.exceptions import ConditionNotMatched
from paasng.platform.applications.models import Application
from paasng.platform.applications.protections import AppResProtector, BaseAppResProtectCondition, ProtectedRes

from .models import ApplicationDescription


def modifications_not_allowed(application: Application, action_name: str = ""):
    if ApplicationDescription.objects.filter(application=application, is_creation=True).exists():
        raise ConditionNotMatched(_("通过描述文件定义的应用不支持该操作"), action_name)


class ApplicationBasicInfoModificationCondition(BaseAppResProtectCondition):
    """Condition for modifying application's basic info(e.g. app name)"""

    action_name = "modify_application_basic_info"

    def validate(self):
        modifications_not_allowed(self.application, self.action_name)


class ApplicationServiceModificationCondition(BaseAppResProtectCondition):
    """Condition for modifying application's service"""

    action_name = "modify_application_services"

    def validate(self):
        modifications_not_allowed(self.application, self.action_name)


AppResProtector.register_precondition(ProtectedRes.BASIC_INFO_MODIFICATIONS, ApplicationBasicInfoModificationCondition)
AppResProtector.register_precondition(ProtectedRes.SERVICES_MODIFICATIONS, ApplicationServiceModificationCondition)
