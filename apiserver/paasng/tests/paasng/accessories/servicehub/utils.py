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

"""Unit tests for ceph provider"""

import uuid

from paasng.accessories.servicehub.services import PlanObj, ServiceObj
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from tests.utils.helpers import generate_random_string

SERVICE_COMMON_ARGS: dict = dict(
    logo="http://logo.com/my.jpg",
    available_languages="all",
    is_visible=True,
)


def gen_service():
    name = generate_random_string()
    return ServiceObj(uuid=str(uuid.uuid4()), name=name, display_name=name, **SERVICE_COMMON_ARGS)


def gen_plan():
    name = generate_random_string()
    return PlanObj(
        uuid=str(uuid.uuid4()),
        name=name,
        description=generate_random_string(),
        is_active=True,
        is_eager=False,
        properties={},
        tenant_id=DEFAULT_TENANT_ID,
    )
