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
import logging
from typing import TYPE_CHECKING

from paasng.dev_resources.services.utils import gen_unique_id

if TYPE_CHECKING:
    from paasng.platform.applications.models import ApplicationEnvironment

logger = logging.getLogger(__name__)


def make_desired_name_by_env(env: 'ApplicationEnvironment') -> str:
    """拼接 ci 资源标识名"""
    long_name = f'{env.module.application.code}-m-{env.module.name}'
    # devops does not support _
    long_name = long_name.replace("_", "0us0")
    return gen_unique_id(name=long_name, namespace="ci", max_length=12)


def make_original_info_by_env(env: 'ApplicationEnvironment') -> str:
    return f"蓝鲸 SaaS 应用<{env.application.code}>-模块<{env.module.name}>-部署环境<{env.environment}>"
