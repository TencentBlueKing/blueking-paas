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
from kubernetes.dynamic import ResourceInstance

from paas_wl.apis.admin.constants import HELM_RELEASE_SECRET_TYPE
from paas_wl.infras.cluster.constants import HelmChartDeployStatus
from paas_wl.infras.cluster.entities import DeployResult, HelmChart, HelmRelease
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.kres import KSecret


class HelmClient:
    """Helm 客户端，用于获取 Helm Release 相关信息"""

    def __init__(self, cluster_name: str):
        self.client = get_client_by_cluster_name(cluster_name)

    def list_releases(self, namespace: str | None = None) -> List[HelmRelease]:
        """获取所有 Helm Release 信息（当前部署的最新版本）"""
        secrets = KSecret(self.client).ops_batch.list(labels={"owner": "helm"}, namespace=namespace).items
        return self._parse_secrets_to_releases(self._filter_latest_version(secrets))

    def get_release(self, name: str, namespace: str | None = None) -> HelmRelease | None:
        """获取指定组件名称的 Helm Release 信息（当前部署的最新版本）"""
        for rel in self.list_releases(namespace):
            if rel.chart.name == name:
                return rel

        return None

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
