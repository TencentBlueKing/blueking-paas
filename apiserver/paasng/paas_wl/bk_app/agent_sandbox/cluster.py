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

import random

from paas_wl.workloads.networking.egress.cluster_state import format_nodes_data
from paas_wl.workloads.networking.egress.models import RegionClusterState


def find_available_port(port_min: int, port_max: int, used_ports: set) -> int | None:
    """查找可用端口"""

    port_count = port_max - port_min + 1
    if len(used_ports) == port_count:
        # 端口已被耗尽
        return None

    # 利用"环形扫描"算法，从随机起点开始查找可用端口，避免展开整个端口范围
    # 随机选一个起始偏移量
    offset = random.randrange(port_count)
    daemon_port = next(
        (p for i in range(port_count) if (p := port_min + (offset + i) % port_count) not in used_ports),
        None,
    )
    return daemon_port


def list_available_hosts(cluster_name: str) -> list[str]:
    """获取集群可用节点 IP 列表

    :param cluster_name: 集群名称
    :returns: 节点 IP 列表，如果没有可用节点则返回空列表
    """
    # 从数据库获取集群最新的节点状态，提取节点 IP 列表
    cluster_state = RegionClusterState.objects.filter(cluster_name=cluster_name).order_by("-created").first()
    if not cluster_state:
        return []

    nodes_data = format_nodes_data(cluster_state.nodes_data)
    node_ips = [node["internal_ip_address"] for node in nodes_data if node.get("internal_ip_address")]

    return node_ips
