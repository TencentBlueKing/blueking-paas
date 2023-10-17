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

from paas_wl.bk_app.monitoring.bklog.managers import AppLogConfigController, NullController
from paasng.platform.applications.models import ModuleEnvironment
from paasng.accessories.log.constants import LogCollectorType
from paasng.accessories.log.shim import get_log_collector_type

logger = logging.getLogger(__name__)


def make_bk_log_controller(env: ModuleEnvironment):
    if get_log_collector_type(env) == LogCollectorType.ELK:
        logger.warning("BkLog is not ready, skip apply BkLogConfig")
        return NullController()
    else:
        return AppLogConfigController(env)
