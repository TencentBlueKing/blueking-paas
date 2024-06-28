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

import uuid

from paasng.accessories.servicehub.remote.manager import RemotePlanObj, RemoteServiceObj
from tests.utils.helpers import generate_random_string

from ..utils import SERVICE_COMMON_ARGS


def gen_service(region: str, specifications: list):
    name = generate_random_string()
    return RemoteServiceObj.from_data(
        region=region,
        service=dict(
            uuid=str(uuid.uuid4()),
            name=name,
            display_name=name,
            specifications=specifications,
            **SERVICE_COMMON_ARGS,
            category=1,
        ),
    )


def gen_plan(region: str, specifications: dict, properties: dict):
    name = generate_random_string()
    properties["region"] = region
    return RemotePlanObj(
        uuid=str(uuid.uuid4()),
        name=name,
        description=generate_random_string(),
        is_active=True,
        is_eager=False,
        region=region,
        specifications=specifications,
        properties=properties,
    )
