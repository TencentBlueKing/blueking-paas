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
from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


def make_bk_log_controller(env: ModuleEnvironment):
    # 如果集群支持蓝鲸日志平台方案, 则会下发 BkLogConfig(如果应用创建了日志采集配置)
    cluster = EnvClusterService(env).get_cluster()
    if not cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR):
        logger.warning("BkLog is not ready, skip apply BkLogConfig")
        return NullController()
    return AppLogConfigController(env)
