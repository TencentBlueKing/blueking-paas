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

from paas_wl.infras.cluster.models import Cluster
from paasng.platform.modules.constants import ExposedURLType

from .constants import AGENT_SANDBOX_ROUTER_SUBDOMAIN_PREFIX


def get_router_endpoint(cluster_name: str) -> str:
    """Get the sandbox router endpoint for a given cluster.
    Remember update 'Agent Sandbox Router' ingress config if the cluster's root
    domain(first domain) update

    The endpoint is derived from the cluster's ingress_config: the router is expected
    to be exposed at:
    - If configure `AGENT_SANDBOX_ROUTER_URL`, return it directly
    - For SUBDOMAIN cluster type: `{prefix}.{default_root_domain}`
    - For SUBPATH cluster type: `{default_root_domain}/{prefix}`

    :param cluster_name: The name of the target cluster
    :returns: The router host string (e.g., "agent-sandbox-router.example.com"
    or "example.com/agent-sandbox-router")
    :raises RuntimeError: If the cluster or its ingress config is missing
    """
    if settings.AGENT_SANDBOX_ROUTER_URL:
        return settings.AGENT_SANDBOX_ROUTER_URL.rstrip("/")

    try:
        cluster = Cluster.objects.get(name=cluster_name)
    except Cluster.DoesNotExist:
        raise RuntimeError(f"cluster {cluster_name!r} not found")

    try:
        if cluster.exposed_url_type == ExposedURLType.SUBDOMAIN:
            root_domain = cluster.ingress_config.default_root_domain.name
            router_endpoint = f"{AGENT_SANDBOX_ROUTER_SUBDOMAIN_PREFIX}.{root_domain}"
        else:
            root_domain = cluster.ingress_config.default_sub_path_domain.name
            router_endpoint = f"{root_domain}/{AGENT_SANDBOX_ROUTER_SUBDOMAIN_PREFIX}"
    except IndexError:
        raise RuntimeError(f"cluster {cluster_name!r} has no ingress config")

    return router_endpoint
