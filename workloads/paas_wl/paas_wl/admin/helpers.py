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
from typing import Dict

from kubernetes.client import ApiException

from paas_wl.resources.base.base import get_client_by_cluster_name
from paas_wl.resources.base.crd import BkApp, DomainGroupMapping
from paas_wl.resources.base.exceptions import ResourceMissing
from paas_wl.resources.base.kres import KCustomResourceDefinition, KDeployment, KNamespace

from .constants import BKPAAS_APP_OPERATOR_INSTALL_NAMESPACE


def detect_operator_status(cluster_name: str) -> Dict:
    """获取指定集群中 Operator 的部署情况"""
    result = {
        'namespace': False,
        'crds': {BkApp.kind: False, DomainGroupMapping.kind: False},
        'controller': {},
    }

    client = get_client_by_cluster_name(cluster_name)

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

    result['controller'] = {
        'replicas': deployments[0]['spec']['replicas'],
        'readyReplicas': deployments[0].get('status', {}).get('readyReplicas', 0),
    }
    return result


def fetch_paas_cobj_info(cluster_name: str, crd_exists: Dict[str, bool]) -> Dict:
    result: Dict[str, Dict] = {BkApp.kind: {}, DomainGroupMapping.kind: {}}
    client = get_client_by_cluster_name(cluster_name)

    # 统计 BkApp 异常 / 正常数量
    if crd_exists[BkApp.kind]:
        bkapps = BkApp(client).ops_label.list(labels={}).items
        ready_cnt = 0
        not_ready_bkapps = []
        for bkapp in bkapps:
            bkapp_name = f"{bkapp['metadata']['namespace']}/{bkapp['metadata']['name']}"

            if hookStatuses := bkapp.get('status', {}).get('hookStatuses', []):
                # 任何 Hook 状态不健康，该 bkapp 都被认为非 ready
                if any([hs.get('phase') != 'Healthy' for hs in hookStatuses]):
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
        domain_group_mappings = DomainGroupMapping(client).ops_label.list(labels={}).items
        result[DomainGroupMapping.kind]['total_cnt'] = len(domain_group_mappings)

    return result
