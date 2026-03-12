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


def get_router_endpoint(cluster_name: str) -> str:
    """Get the sandbox router endpoint for a given cluster.

    The endpoint is derived from the cluster's ingress_config: the router is expected
    to be exposed at ``agent-sbx-router.{default_root_domain}``.

    :param cluster_name: The name of the target cluster.
    :returns: The router host string (e.g., "agent-sbx-router.apps.example.com").
    :raises RuntimeError: If the cluster or its ingress config is missing.
    """
    try:
        cluster = Cluster.objects.get(name=cluster_name)
    except Cluster.DoesNotExist:
        raise RuntimeError(f"cluster {cluster_name!r} not found")

    root_domain = cluster.ingress_config.default_root_domain.name
    prefix = settings.AGENT_SANDBOX_ROUTER_SUBDOMAIN_PREFIX
    return f"{prefix}.{root_domain}"
