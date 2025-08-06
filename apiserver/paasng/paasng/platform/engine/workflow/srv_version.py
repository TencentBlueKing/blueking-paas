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

import logging
from typing import Dict, Tuple

from django.conf import settings
from django.core.cache import cache

from paas_wl.infras.cluster.helm import HelmClient
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class ServerVersionChecker:
    """检查 apiserver 和 operator 版本信息是否一致"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def check_version(self) -> Tuple[bool, Dict]:
        """检查 apiserver 和 operator 版本是否一致

        :param env: 应用环境对象
        :returns: (是否一致, 版本信息)
        """
        # 初始化返回信息
        versions = {"apiserver": "", "operator": ""}

        # 只有部署云原生应用才需要检测
        if self.env.application.type != ApplicationType.CLOUD_NATIVE:
            return True, versions

        # apiserver 版本信息, 根据 Helm 构建时, 注入容器的 env
        apiserver_version = settings.BKPAAS_APISERVER_VERSION
        versions["apiserver"] = apiserver_version

        # 仅在打开检查开关和获取到 apiserver_version 的时候才需要检查
        if not settings.BKPAAS_OPERATOR_VERSION_CHECK or not apiserver_version:
            return True, versions

        # operator 版本信息, 通过 helm 客户端获取
        cluster_name = EnvClusterService(self.env).get_cluster_name()
        cache_key = f"helm_release:{cluster_name}:operator_version"
        operator_version = cache.get(cache_key)
        if operator_version is None:
            operator_release = HelmClient(cluster_name).get_release("bkpaas-app-operator")
            operator_version = operator_release.chart.app_version if operator_release else ""

            if operator_version == apiserver_version:
                # 通常 apiserver 会先于 operator 升级.
                # 基于这一前提, 缓存时间设置为 24h, 进一步减少查询 helm release 的频次
                cache.set(cache_key, operator_version, 24 * 60 * 60)

        versions["operator"] = operator_version

        if operator_version != apiserver_version:
            # 版本不一致时, 主动清理缓存, 促使下次强制刷新
            cache.delete(cache_key)
            return False, versions

        return True, versions
