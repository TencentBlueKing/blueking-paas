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
from typing import Any

from blue_krill.cubing_case import shortcuts

from paas_wl.bk_app.cnative.specs.constants import DEFAULT_RES_QUOTA_PLAN_NAME
from paasng.platform.bkapp_model.models import ResQuotaPlan

logger = logging.getLogger(__name__)


def get_quota_plan(spec_plan_name: str) -> str:
    """Get ProcessSpecPlan by name"""
    # TODO: fix circular import
    from paas_wl.bk_app.processes.models import ProcessSpecPlan

    # Note: First try to find in ResQuotaPlan, then fallback to ProcessSpecPlan
    active_plans = {plan_obj.name: plan_obj for plan_obj in ResQuotaPlan.objects.filter(is_active=True)}
    if plan_obj := active_plans.get(spec_plan_name):
        return plan_obj.name

    logger.debug("unknown ResQuotaPlan name `%s`, try to get ProcessSpecPlan", spec_plan_name)

    try:
        spec_plan: ProcessSpecPlan = ProcessSpecPlan.objects.get_by_name(name=spec_plan_name)
    except ProcessSpecPlan.DoesNotExist:
        default = active_plans.get(DEFAULT_RES_QUOTA_PLAN_NAME)
        if not default:
            raise RuntimeError(f"default res quota plan `{DEFAULT_RES_QUOTA_PLAN_NAME}` not found")
        return default.name

    return spec_plan.name


def camel_to_snake_case(data: Any) -> Any:
    """convert all camel case field name to snake case, and return the converted obj"""
    if isinstance(data, dict):
        return {shortcuts.to_lower_snake_case(key): camel_to_snake_case(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [camel_to_snake_case(item) for item in data]
    return data
