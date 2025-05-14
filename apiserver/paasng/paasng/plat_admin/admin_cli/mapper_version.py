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

import datetime
import uuid
from typing import Dict, Iterable

from django.conf import settings
from typing_extensions import TypeAlias

from paas_wl.bk_app.applications.models.config import Config
from paasng.platform.applications.models import ModuleEnvironment

WlAppId: TypeAlias = uuid.UUID


def get_mapper_v1_envs() -> Iterable[ModuleEnvironment]:
    """Get all environments that use resource mapper "v1" rule.

    :return: An iterable of ModuleEnvironment objects.
    """
    processed: Dict[WlAppId, datetime.datetime] = {}
    version_map: Dict[WlAppId, str] = {}
    for config in Config.objects.all().iterator():
        # Ignore older configs
        if (last_created := processed.get(config.app_id)) and config.created < last_created:
            continue
        processed[config.app_id] = config.created

        m = config.metadata or {}
        version_map[config.app_id] = m.get("mapper_version", settings.GLOBAL_DEFAULT_MAPPER_VERSION)

    # Filter and print all envs that use v1
    for app_id, ver in version_map.items():
        if ver != "v1":
            continue
        try:
            env = ModuleEnvironment.objects.get(engine_app_id=app_id)
        except ModuleEnvironment.DoesNotExist:
            continue

        yield env
