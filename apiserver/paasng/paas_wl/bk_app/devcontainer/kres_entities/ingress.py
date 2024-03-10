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
from dataclasses import dataclass
from typing import List

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.devcontainer.conf import get_ingress_path_backends
from paas_wl.bk_app.devcontainer.entities import IngressDomain
from paas_wl.bk_app.devcontainer.kres_slzs import DevContainerIngressDeserializer, DevContainerIngressSerializer
from paas_wl.infras.cluster.utils import get_dev_mode_cluster
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity
from paas_wl.workloads.networking.entrance.utils import to_dns_safe

from .service import get_service_name


@dataclass
class DevContainerIngress(AppEntity):
    """Ingress entity to expose DevContainerService"""

    domains: List[IngressDomain]

    class Meta:
        kres_class = kres.KIngress
        serializer = DevContainerIngressSerializer
        deserializer = DevContainerIngressDeserializer

    def __post_init__(self):
        self.rewrite_to_root = True
        self.set_header_x_script_name = True

    @classmethod
    def create(cls, dev_wl_app: WlApp, app_code: str) -> "DevContainerIngress":
        service_name = get_service_name(dev_wl_app)
        sub_domain = IngressDomain(
            host=get_sub_domain_host(app_code, dev_wl_app, dev_wl_app.module_name),
            path_backends=get_ingress_path_backends(service_name),
        )
        return cls(app=dev_wl_app, name=get_ingress_name(dev_wl_app), domains=[sub_domain])


def get_ingress_name(dev_wl_app: WlApp) -> str:
    return dev_wl_app.scheduler_safe_name


def get_sub_domain_host(app_code: str, wl_app: WlApp, module_name: str) -> str:
    cluster = get_dev_mode_cluster(wl_app)
    root_domain = cluster.ingress_config.default_root_domain.name
    safe_parts = [to_dns_safe(s) for s in ["dev", module_name, app_code]]
    return ("-dot-".join(safe_parts) + "." + root_domain).lower()
