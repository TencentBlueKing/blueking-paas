# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
from semver import VersionInfo

from paas_wl.infras.cluster.helm import HelmClient
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.exceptions import ServerVersionCheckFailed

logger = logging.getLogger(__name__)


def parse_xyz_version(version: str | None) -> tuple[int, int, int] | None:
    """解析版本号中的 X.Y.Z(major.minor.patch), 无法解析时返回 None

    :param version: 形如 "1.8.0"、"1.7.0-beta.5" 的版本号
    """
    if not version:
        return None

    try:
        parsed = VersionInfo.parse(version.strip())
    except (TypeError, ValueError):
        return None

    return parsed.major, parsed.minor, parsed.patch


class ServerVersionChecker:
    """检查 apiserver 和 operator 版本信息是否兼容

    仅比较版本号中的 X.Y.Z; X.Y.Z 相同而只有预发布号(alpha/beta/rc)不同时,
    属于滚动升级过程中的正常中间状态, 放行部署并记录 WARNING 日志.
    """

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def validate_version(self):
        """检查 apiserver 和 operator 版本是否兼容, 不兼容时抛出 ServerVersionCheckFailed"""

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
            try:
                operator_release = HelmClient(cluster_name).get_release("bkpaas-app-operator")
            except Exception:
                # 查询失败时视作 operator 版本缺失, 同样中止部署
                logger.exception("failed to get the version of bkpaas-app-operator in cluster %s", cluster_name)
                operator_version = ""
            else:
                operator_version = operator_release.chart.app_version if operator_release else ""

            # 完整版本号一致时缓存查询结果, 减少 Helm 查询次数; 缓存过期后会重新查询, 避免掩盖版本变化
            if operator_version == apiserver_version:
                cache.set(cache_key, operator_version)

        apiserver_xyz = parse_xyz_version(apiserver_version)
        operator_xyz = parse_xyz_version(operator_version)

        # 版本缺失或无法解析时, 无法确认两者是否兼容, 中止部署
        if apiserver_xyz is None or operator_xyz is None:
            cache.delete(cache_key)
            raise ServerVersionCheckFailed(
                _(
                    "平台未正常部署，无法进行操作，请联系管理员。组件版本格式无法识别：apiserver:'{}', operator:'{}'"
                ).format(apiserver_version, operator_version)
            )

        # X.Y.Z 不同意味着存在不兼容的变更, 中止部署
        if apiserver_xyz != operator_xyz:
            # 通常 apiserver 会先于 operator 升级. 版本不一致时, 主动清理缓存, 促使下次强制刷新
            cache.delete(cache_key)
            raise ServerVersionCheckFailed(
                _("平台未正常部署，无法进行操作，请联系管理员。组件版本不一致：apiserver:'{}', operator:'{}'").format(
                    apiserver_version, operator_version
                )
            )

        if operator_version == apiserver_version:
            return

        # X.Y.Z 一致, 仅预发布号不同, 属于滚动升级的正常状态, 放行但记录告警
        logger.warning(
            "apiserver and operator versions differ but share the same X.Y.Z, "
            "allowing deployment: apiserver='%s', operator='%s'",
            apiserver_version,
            operator_version,
        )
