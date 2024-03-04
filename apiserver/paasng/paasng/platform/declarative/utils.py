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
import logging
from operator import itemgetter
from typing import Any

from blue_krill.cubing_case import shortcuts
from kubernetes.utils import parse_quantity

from paas_wl.bk_app.cnative.specs.crd import bk_app
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP

logger = logging.getLogger(__name__)


def get_quota_plan(spec_plan_name: str) -> bk_app.ResQuotaPlan:
    """Get ProcessSpecPlan by name and transform it to ResQuotaPlan"""
    # TODO: fix circular import
    from paas_wl.bk_app.processes.models import ProcessSpecPlan

    try:
        return bk_app.ResQuotaPlan(spec_plan_name)
    except ValueError:
        logger.debug("unknown ResQuotaPlan value `%s`, try to convert ProcessSpecPlan to ResQuotaPlan", spec_plan_name)

    try:
        spec_plan = ProcessSpecPlan.objects.get_by_name(name=spec_plan_name)
    except ProcessSpecPlan.DoesNotExist:
        return bk_app.ResQuotaPlan.P_DEFAULT

    # Memory 稀缺性比 CPU 要高, 转换时只关注 Memory
    limits = spec_plan.get_resource_summary()["limits"]
    expected_limit_memory = parse_quantity(limits.get("memory", "512Mi"))
    quota_plan_memory = sorted(
        ((parse_quantity(limit.memory), quota_plan) for quota_plan, limit in PLAN_TO_LIMIT_QUOTA_MAP.items()),
        key=itemgetter(0),
    )
    for limit_memory, quota_plan in quota_plan_memory:
        if limit_memory >= expected_limit_memory:
            return quota_plan
    return quota_plan_memory[-1][1]


def camel_to_snake_case(data: Any) -> Any:
    """convert all camel case field name to snake case, and return the converted obj"""
    if isinstance(data, dict):
        return {shortcuts.to_lower_snake_case(key): camel_to_snake_case(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [camel_to_snake_case(item) for item in data]
    return data
