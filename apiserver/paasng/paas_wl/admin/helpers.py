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
import base64
import gzip
import json
from dataclasses import dataclass
from typing import Any, Dict, List

import arrow
import yaml
from kubernetes.client import ApiException
from kubernetes.dynamic import ResourceInstance

from paas_wl.admin.constants import BKPAAS_APP_OPERATOR_INSTALL_NAMESPACE, HELM_RELEASE_SECRET_TYPE
from paas_wl.cnative.specs.constants import ApiVersion
from paas_wl.resources.base.base import EnhancedApiClient
from paas_wl.resources.base.crd import BkApp, DomainGroupMapping
from paas_wl.resources.base.exceptions import ResourceMissing
from paas_wl.resources.base.kres import KCustomResourceDefinition, KDaemonSet, KDeployment, KNamespace, KStatefulSet


def detect_operator_status(client: EnhancedApiClient) -> Dict:
    """获取指定集群中 Operator 的部署情况"""
    result = {
        'namespace': False,
        'crds': {BkApp.kind: False, DomainGroupMapping.kind: False},
        'controller': {},
    }

    # 检查集群中是否存在 Operator 需要的 CRD 定义
    for crd in KCustomResourceDefinition(client).ops_label.list(labels={}).items:
        crd_kind = crd['spec']['names']['kind']
        if crd_kind in [BkApp.kind, DomainGroupMapping.kind]:
            result['crds'][crd_kind] = True  # type: ignore

    # 检查 controller 部署的命名空间是否存在
    try:
        KNamespace(client).get(name=BKPAAS_APP_OPERATOR_INSTALL_NAMESPACE)
    except (ResourceMissing, ApiException):
        return result
    else:
        result['namespace'] = True

    deployments = (
        KDeployment(client)
        .ops_label.list(
            labels={'control-plane': 'controller-manager'},
            namespace=BKPAAS_APP_OPERATOR_INSTALL_NAMESPACE,
        )
        .items
    )
    if not deployments:
        return result

    # 获取 controller 副本状态
    result['controller'] = {
        'replicas': deployments[0]['spec']['replicas'],
        'readyReplicas': deployments[0].get('status', {}).get('readyReplicas', 0),
    }
    return result


def fetch_paas_cobj_info(client: EnhancedApiClient, crd_exists: Dict[str, bool]) -> Dict:
    result: Dict[str, Dict] = {BkApp.kind: {}, DomainGroupMapping.kind: {}}

    # 统计 BkApp NotReady & 总数量
    if crd_exists[BkApp.kind]:
        bkapps = BkApp(client).ops_label.list(labels={}).items
        ready_cnt = 0
        not_ready_bkapps = []
        for bkapp in bkapps:
            bkapp_name = f"{bkapp['metadata']['namespace']}/{bkapp['metadata']['name']}"

            if hookStatuses := bkapp.get('status', {}).get('hookStatuses', []):
                # 任何 Hook 状态不健康，该 bkapp 都被认为非 ready
                if any(hs.get('phase') != 'Healthy' for hs in hookStatuses):
                    not_ready_bkapps.append(bkapp_name)
                    continue

            # bkapp 总状态需要是 Running 才能算是 ready 的
            if bkapp.get('status', {}).get('phase') != 'Running':
                not_ready_bkapps.append(bkapp_name)
                continue

            ready_cnt += 1

        result[BkApp.kind] = {'total_cnt': len(bkapps), 'ready_cnt': ready_cnt, 'not_ready_bkapps': not_ready_bkapps}

    # 统计 DomainGroupMapping 数量
    if crd_exists[DomainGroupMapping.kind]:
        domain_group_mappings = (
            DomainGroupMapping(client, api_version=ApiVersion.V1ALPHA1).ops_label.list(labels={}).items
        )
        result[DomainGroupMapping.kind]['total_cnt'] = len(domain_group_mappings)

    return result


@dataclass
class DeployResult:
    # 部署状态
    status: str
    # 部署详情
    description: str
    # 部署时间
    created_at: str


@dataclass
class HelmChart:
    # Chart 名称
    name: str
    # Chart 版本
    version: str
    # App 版本
    app_version: str
    # Chart 描述
    description: str


@dataclass
class HelmRelease:
    # release 名称
    name: str
    # 部署的命名空间
    namespace: str
    # release 版本
    version: int
    # chart 信息
    chart: HelmChart
    # 部署信息
    deploy_result: DeployResult
    # 部署的 k8s 资源信息
    resources: List[Dict[str, Any]]
    # 存储 release secret 名称
    secret_name: str


class HelmReleaseParser:
    def __init__(self, secret: ResourceInstance, parse_manifest: bool = False):
        """
        :param secret: 存储 Helm Release 信息的 Secret 对象
        :param parse_manifest: 是否解析 manifest 内容以生成资源信息
        """
        self.secret = secret
        self.parse_manifest = parse_manifest

    def parse(self) -> HelmRelease:
        """
        解析 Helm Release 信息
        :return: HelmRelease 对象
        """
        release = json.loads(gzip.decompress(base64.b64decode(base64.b64decode(self.secret.data.release))))
        release_info = release['info']
        chart_metadata = release['chart']['metadata']

        resources: List[Dict] = []
        if self.parse_manifest:
            resources = yaml.safe_load_all(release['manifest'])  # type: ignore

        return HelmRelease(
            name=release['name'],
            namespace=release['namespace'],
            version=release['version'],
            chart=HelmChart(
                name=chart_metadata['name'],
                version=chart_metadata['version'],
                app_version=chart_metadata.get('appVersion'),
                description=chart_metadata.get('description'),
            ),
            deploy_result=DeployResult(
                status=release_info['status'],
                description=release_info['description'],
                created_at=arrow.get(release_info['last_deployed']).datetime.isoformat(' ', 'seconds'),
            ),
            resources=resources,
            secret_name=self.secret.metadata.name,
        )


def convert_secrets_to_releases(secrets: List[ResourceInstance]) -> List[HelmRelease]:
    """将 Secret（type=helm.sh/release.v1） 转换为 Helm Release"""
    return [HelmReleaseParser(s).parse() for s in secrets if s.type == HELM_RELEASE_SECRET_TYPE]


def filter_latest_releases(releases: List[HelmRelease]) -> List[HelmRelease]:
    """过滤出最新的 Helm Release"""
    release_map: Dict[str, HelmRelease] = {}
    for rel in releases:
        if rel.name not in release_map or rel.version > release_map[rel.name].version:
            release_map[rel.name] = rel

    return release_map.values()  # type: ignore


class WorkloadsDetector:
    """组件状态探测器"""

    def __init__(self, client: EnhancedApiClient, release: HelmRelease):
        self.client = client
        self.release = release

    def get_statuses(self) -> List[Dict[str, Any]]:
        if not self.release.resources:
            return []

        return [
            self._get_status(res['kind'], self.release.namespace, res['metadata']['name'])
            for res in self.release.resources
            if res['kind'] in [KDeployment.kind, KStatefulSet.kind, KDaemonSet.kind]
        ]

    def _get_status(self, kind: str, namespace: str, name: str) -> Dict[str, Any]:
        """获取工作负载资源状态"""
        kres_client, gen_status_func = {
            KDeployment.kind: (KDeployment, self._gen_deploy_status),
            KStatefulSet.kind: (KStatefulSet, self._gen_sts_status),
            KDaemonSet.kind: (KDaemonSet, self._gen_ds_status),
        }[kind]

        res = kres_client(self.client).get(namespace=namespace, name=name)
        return {
            'kind': kind,
            'name': name,
            'status': gen_status_func(res),
            'conditions': res.status.get('conditions', []),
        }

    def _gen_deploy_status(self, res: ResourceInstance):
        ready = res.status.get('readyReplicas', 0)
        replicas = res.spec.get('replicas', 0)
        updated = res.status.get('updatedReplicas', 0)
        available = res.status.get('availableReplicas', 0)
        return f'Ready: {ready}/{replicas}, Up-to-date: {updated}, Available: {available}'

    def _gen_sts_status(self, res: ResourceInstance):
        ready = res.status.get('readyReplicas', 0)
        replicas = res.spec.get('replicas', 0)
        updated = res.status.get('updatedReplicas', 0)
        return f'Ready: {ready}/{replicas}, Up-to-date: {updated}'

    def _gen_ds_status(self, res: ResourceInstance):
        desired = res.status.get('desiredNumberScheduled', 0)
        current = res.status.get('currentNumberScheduled', 0)
        ready = res.status.get('numberReady', 0)
        updated = res.status.get('updatedNumberScheduled', 0)
        available = res.status.get('numberAvailable', 0)
        return f'Desired: {desired}, Current: {current}, Ready: {ready}, Up-to-date: {updated}, Available: {available}'
