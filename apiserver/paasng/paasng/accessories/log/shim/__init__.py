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

from django.conf import settings

from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.accessories.log.constants import LogCollectorType
from paasng.accessories.log.shim.setup_bklog import setup_bk_log_custom_collector, setup_default_bk_log_model
from paasng.accessories.log.shim.setup_bklog_shared import (
    setup_shared_bk_log_custom_collector,
    setup_shared_bk_log_model,
    should_use_shared_bk_log_index,
)
from paasng.accessories.log.shim.setup_elk import setup_saas_elk_model
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import ModuleEnvironment


def get_log_collector_type(env: ModuleEnvironment) -> LogCollectorType:
    cluster = EnvClusterService(env).get_cluster()
    if _should_use_bk_log_collector(
        env,
        cluster_has_bk_log=cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR),
    ):
        return LogCollectorType.BK_LOG
    return LogCollectorType.ELK


def setup_env_log_model(env: ModuleEnvironment):
    cluster = EnvClusterService(env).get_cluster()
    cluster_has_bk_log = cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR)
    use_shared_bk_log_index = _should_use_shared_bk_log_index(env)

    # 如果集群支持蓝鲸日志平台方案, 则创建内置自定义采集项配置。
    # 创建自定义采集项配置后, 应用部署时将会下发 BkLogConfig。
    if settings.ENABLE_BK_MONITOR and cluster_has_bk_log:
        _setup_bk_log_custom_collector(env, use_shared_bk_log_index)

    if _should_use_bk_log_collector(env, cluster_has_bk_log):
        return _setup_bk_log_model(env, use_shared_bk_log_index)

    if settings.LOG_COLLECTOR_TYPE != LogCollectorType.ELK:
        raise ValueError("ELK is not supported")
    return setup_saas_elk_model(env)


def _should_use_bk_log_collector(env: ModuleEnvironment, cluster_has_bk_log: bool) -> bool:
    return (
        settings.ENABLE_BK_MONITOR
        and env.application.feature_flag.has_feature(AppFeatureFlag.ENABLE_BK_LOG_COLLECTOR)
        and cluster_has_bk_log
    )


def _should_use_shared_bk_log_index(env: ModuleEnvironment) -> bool:
    return should_use_shared_bk_log_index(env.module)


def _setup_bk_log_custom_collector(env: ModuleEnvironment, use_shared_bk_log_index: bool):
    if use_shared_bk_log_index:
        return setup_shared_bk_log_custom_collector(env.module)
    return setup_bk_log_custom_collector(env.module)


def _setup_bk_log_model(env: ModuleEnvironment, use_shared_bk_log_index: bool):
    if use_shared_bk_log_index:
        return setup_shared_bk_log_model(env)
    return setup_default_bk_log_model(env)
