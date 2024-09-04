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

from typing import Optional

from paasng.platform.bkapp_model.entities import Observability
from paasng.platform.bkapp_model.models import ObservabilityConfig
from paasng.platform.modules.models import Module

from .result import CommonSyncResult


def sync_observability(module: Module, observability: Optional[Observability]) -> CommonSyncResult:
    """Sync observability config to db model"""
    ret = CommonSyncResult()

    if not observability or not observability.monitoring:
        ret.deleted_num, _ = ObservabilityConfig.objects.filter(module=module).delete()
        return ret

    _, created = ObservabilityConfig.objects.update_or_create(
        module=module, defaults={"monitoring": observability.monitoring}
    )
    ret.incr_by_created_flag(created)

    return ret
