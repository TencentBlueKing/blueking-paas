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

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _

from paas_wl.infras.cluster.helm import HelmClient
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.exceptions import ServerVersionCheckFailed

logger = logging.getLogger(__name__)


class ServerVersionChecker:
    """检查 apiserver 和 operator 版本信息是否一致"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def validate_version(self):
        """检查 apiserver 和 operator 版本是否一致"""

        # 只有部署云原生应用才需要检测
        if self.env.application.type != ApplicationType.CLOUD_NATIVE:
            return

        # apiserver 版本信息, 根据 Helm 构建时, 注入容器的 env
        apiserver_version = settings.APISERVER_VERSION

        # 仅在打开检查开关和获取到 apiserver_version 的时候才需要检查
        if not settings.APISERVER_OPERATOR_VERSION_CHECK or not apiserver_version:
            return

        # operator 版本信息, 通过 helm 客户端获取
        cluster_name = EnvClusterService(self.env).get_cluster_name()
        cache_key = f"helm_release:{cluster_name}:operator_version"
        operator_version = cache.get(cache_key)
        if operator_version is None:
            operator_release = HelmClient(cluster_name).get_release("bkpaas-app-operator")
            operator_version = operator_release.chart.app_version if operator_release else ""

            if operator_version == apiserver_version:
                cache.set(cache_key, operator_version)

        if operator_version != apiserver_version:
            # 通常 apiserver 会先于 operator 升级. 版本不一致时, 主动清理缓存, 促使下次强制刷新
            cache.delete(cache_key)
            raise ServerVersionCheckFailed(
                _(
                    "平台未正常部署，无法进行操作，请联系管理员。组件版本不一致：apiserver:'{}', operator:'{}'".format(
                        apiserver_version, operator_version
                    )
                )
            )

        return
