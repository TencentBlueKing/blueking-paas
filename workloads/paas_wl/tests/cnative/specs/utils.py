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
from typing import List, Literal

from paas_wl.cnative.specs.constants import MResConditionType, MResPhaseType
from paas_wl.cnative.specs.models import create_app_resource
from paas_wl.cnative.specs.v1alpha1.bk_app import BkAppResource, MetaV1Condition


def create_condition(
    type_: MResConditionType,
    status: Literal["True", "False", "Unknown"] = "Unknown",
    reason: str = '',
    message: str = '',
) -> MetaV1Condition:
    return MetaV1Condition(
        type=type_,
        status=status,
        reason=reason,
        message=message,
    )


def create_res_with_conds(
    conditions: List[MetaV1Condition], phase: MResPhaseType = MResPhaseType.AppPending
) -> BkAppResource:
    mres = create_app_resource(name="foo", image="nginx:latest")
    mres.status.conditions = conditions
    mres.status.phase = phase
    return mres
