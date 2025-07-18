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

import base64
import gzip
import json
from typing import Dict, List

import arrow
import yaml
from django.core.cache import cache
from kubernetes.dynamic import ResourceInstance

from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.kres import KSecret
from paasng.plat_mgt.infras.clusters.constants import HELM_RELEASE_SECRET_TYPE, HelmChartDeployStatus
from paasng.plat_mgt.infras.clusters.entities import DeployResult, HelmChart, HelmRelease


class HelmClient:
    """Helm 客户端，用于获取 Helm Release 相关信息"""

    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name
        self.client = get_client_by_cluster_name(cluster_name)

    def list_releases(self, namespace: str | None = None, use_cache: bool = True) -> List[HelmRelease]:
        """获取所有 Helm Release 信息（当前部署的最新版本）"""
        if use_cache:
            cache_key = f"helm_releases:{self.cluster_name}:{namespace or 'all'}"
            cached_releases = cache.get(cache_key)
            if cached_releases is not None:
                return cached_releases

        secrets = KSecret(self.client).ops_batch.list(labels={"owner": "helm"}, namespace=namespace).items
        releases = self._parse_secrets_to_releases(self._filter_latest_version(secrets))

        if use_cache:
            # 缓存 5 分钟
            cache.set(cache_key, releases, 60 * 5)

        return releases

    def get_release(self, name: str, namespace: str | None = None, use_cache: bool = True) -> HelmRelease | None:
        """获取指定组件名称的 Helm Release 信息（当前部署的最新版本）"""
        if use_cache:
            cache_key = f"helm_releases:{self.cluster_name}:{namespace or 'all'}:{name}"
            cached_release = cache.get(cache_key)
            if cached_release is not None:
                return cached_release

        for rel in self.list_releases(namespace, use_cache=use_cache):
            if rel.chart.name == name:
                if use_cache:
                    # 缓存 5 分钟
                    cache.set(cache_key, rel, 60 * 5)
                return rel

        if use_cache:
            # 如果没有找到，缓存 None 以避免重复查询
            cache.set(cache_key, None, 60 * 5)
        return None

    def clear_cache(self, namespace: str | None = None, name: str | None = None):
        """清理缓存"""
        if name:
            # 清理指定 release 的缓存
            cache_key = f"helm_release:{self.cluster_name}:{namespace or 'all'}:{name}"
            cache.delete(cache_key)
        else:
            # 清理所有 releases 的缓存
            cache_key = f"helm_releases:{self.cluster_name}:{namespace or 'all'}"
            cache.delete(cache_key)

    @staticmethod
    def _filter_latest_version(secrets: List[ResourceInstance]) -> List[ResourceInstance]:
        """过滤出最新的 Helm Release"""
        secret_map: Dict[str, ResourceInstance] = {}
        release_version_map: Dict[str, int] = {}
        for s in secrets:
            labels = s.metadata.labels
            try:
                release_name, version = labels["name"], int(labels["version"])
            except Exception:
                # 忽略异常数据
                continue

            if release_name not in release_version_map or version > release_version_map[release_name]:
                secret_map[release_name] = s
                release_version_map[release_name] = version

        return list(secret_map.values())

    @staticmethod
    def _parse_secrets_to_releases(secrets: List[ResourceInstance]) -> List[HelmRelease]:
        """将存储 Helm Release 信息的 Secret 解析成 HelmRelease 对象"""
        return [HelmReleaseParser(s).parse() for s in secrets if s.type == HELM_RELEASE_SECRET_TYPE]


class HelmReleaseParser:
    """解析 Helm Release 数据"""

    def __init__(self, secret: ResourceInstance):
        """
        :param secret: 存储 Helm Release 信息的 Secret 对象
        """
        self.secret = secret

    def parse(self) -> HelmRelease:
        """
        解析 Helm Release 信息
        :return: HelmRelease 对象
        """
        release = json.loads(gzip.decompress(base64.b64decode(base64.b64decode(self.secret.data.release))))
        release_info = release["info"]
        chart_metadata = release["chart"]["metadata"]

        return HelmRelease(
            name=release["name"],
            namespace=release["namespace"],
            version=release["version"],
            chart=HelmChart(
                name=chart_metadata["name"],
                version=chart_metadata["version"],
                app_version=chart_metadata.get("appVersion"),
                description=chart_metadata.get("description"),
            ),
            deploy_result=DeployResult(
                status=HelmChartDeployStatus(release_info["status"]),
                description=release_info["description"],
                created_at=arrow.get(release_info["last_deployed"]).datetime,
            ),
            values=release.get("config", {}),
            resources=list(yaml.safe_load_all(release.get("manifest", ""))),
            secret_name=self.secret.metadata.name,
        )
