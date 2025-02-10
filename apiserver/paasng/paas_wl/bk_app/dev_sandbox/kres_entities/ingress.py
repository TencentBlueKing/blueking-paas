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

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from paas_wl.bk_app.dev_sandbox.conf import get_network_configs
from paas_wl.bk_app.dev_sandbox.entities import IngressDomain, IngressPathBackend
from paas_wl.bk_app.dev_sandbox.kres_slzs import DevSandboxIngressDeserializer, DevSandboxIngressSerializer
from paas_wl.bk_app.dev_sandbox.names import get_dev_sandbox_ingress_name, get_dev_sandbox_service_name
from paas_wl.infras.cluster.utils import get_dev_sandbox_cluster
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity
from paas_wl.workloads.networking.entrance.utils import to_dns_safe

if TYPE_CHECKING:
    from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox


@dataclass
class DevSandboxIngress(AppEntity):
    domains: List[IngressDomain]

    class Meta:
        kres_class = kres.KIngress
        serializer = DevSandboxIngressSerializer
        deserializer = DevSandboxIngressDeserializer

    def __post_init__(self):
        self.rewrite_to_root = True
        self.set_header_x_script_name = True

    @classmethod
    def create(cls, dev_sandbox: "DevSandbox") -> "DevSandboxIngress":
        path_backends = _get_path_backends(dev_sandbox)
        sub_domain = IngressDomain(
            host=_get_sub_domain_host(dev_sandbox),
            path_backends=path_backends,
        )
        return cls(app=dev_sandbox.app, name=get_dev_sandbox_ingress_name(dev_sandbox.app), domains=[sub_domain])


def _get_path_backends(dev_sandbox: "DevSandbox") -> List[IngressPathBackend]:
    return [
        IngressPathBackend(
            path_prefix=f"/dev_sandbox/{dev_sandbox.code}{cfg.path_prefix}",
            service_name=get_dev_sandbox_service_name(dev_sandbox.app),
            service_port_name=cfg.svc_port_name,
        )
        for cfg in get_network_configs(dev_sandbox)
    ]


def _get_sub_domain_host(dev_sandbox: "DevSandbox") -> str:
    wl_app = dev_sandbox.app
    cluster = get_dev_sandbox_cluster(wl_app)
    root_domain = cluster.ingress_config.default_root_domain.name
    safe_parts = [to_dns_safe(s) for s in ["dev", wl_app.module_name, wl_app.paas_app_code]]
    return ("-dot-".join(safe_parts) + "." + root_domain).lower()
