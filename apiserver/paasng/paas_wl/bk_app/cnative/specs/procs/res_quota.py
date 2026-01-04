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

from collections.abc import Callable


class ResQuotaPlanData:
    """A simple data class to hold ResQuotaPlan information"""

    def __init__(self, name: str, limits: dict, requests: dict, is_active: bool, is_builtin: bool):
        self.name = name
        self.limits = limits
        self.requests = requests
        self.is_active = is_active
        self.is_builtin = is_builtin


# Type alias for getter function
ResQuotaPlanGetter = Callable[[], dict[str, ResQuotaPlanData]]

# Global variable to hold the getter function
_res_quota_plan_getter: ResQuotaPlanGetter | None = None


def set_res_quota_plan_getter(getter: ResQuotaPlanGetter):
    """Set the global ResQuotaPlan getter function

    :param getter: A function that returns a dict of ResQuotaPlanData
    """
    global _res_quota_plan_getter
    _res_quota_plan_getter = getter


def get_active_res_quota_plans() -> dict[str, ResQuotaPlanData]:
    """Get all active ResQuotaPlans using the registered getter function

    :return: A dict of ResQuotaPlanData
    :raises ValueError: If no getter function has been registered
    """
    if _res_quota_plan_getter is None:
        raise ValueError("No ResQuotaPlan getter function has been registered")
    return _res_quota_plan_getter()
