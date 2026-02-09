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

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.dev_sandbox.entities import IngressDomain, IngressPathBackend
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer
from paas_wl.workloads.networking.ingress.constants import (
    ANNOT_CONFIGURATION_SNIPPET,
    ANNOT_REWRITE_TARGET,
    ANNOT_SKIP_FILTER_CLB,
    ANNOT_SSL_REDIRECT,
)
from paas_wl.workloads.networking.ingress.kres_slzs.utils import NginxRegexRewrittenProvider
from paas_wl.workloads.networking.ingress.managers import get_ingress_class_by_wl_app

if TYPE_CHECKING:
    from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandboxIngress


class DevSandboxIngressSerializer(AppEntitySerializer["DevSandboxIngress"]):
    """Serializer for DevContainerIngress in ApiVersion networking.k8s.io/v1, which is available in k8s 1.19+

    IMPORTANT: This class is not compatible with ingress-nginx < 1.0
    Ref: https://kubernetes.github.io/ingress-nginx/deploy/#running-on-kubernetes-versions-older-than-119

    参考 paas_wl.workloads.networking.ingress.kres_slzs.ingress.IngressV1Serializer 实现
    """

    @staticmethod
    def get_api_version_from_gvk(gvk_config):
        return "networking.k8s.io/v1"

    def serialize(self, obj: "DevSandboxIngress", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        """serialize obj into Ingress(networking.k8s.io/v1)"""
        nginx_adaptor = NginxRegexRewrittenProvider()
        annotations = {
            # Disable HTTPS redirect by default, the behaviour might be overwritten in the future
            ANNOT_SSL_REDIRECT: "false",
            ANNOT_SKIP_FILTER_CLB: "true",
        }
        if obj.rewrite_to_root:
            annotations[ANNOT_REWRITE_TARGET] = nginx_adaptor.make_rewrite_target()
        if obj.set_header_x_script_name:
            annotations[ANNOT_CONFIGURATION_SNIPPET] = nginx_adaptor.make_configuration_snippet()

        # ingressClassName
        if ingress_cls_name := get_ingress_class_by_wl_app(obj.app):
            annotations["kubernetes.io/ingress.class"] = ingress_cls_name

        # tls 证书 Secrets
        tls_group_by_secret_name: Dict[str, List] = defaultdict(list)
        for domain in obj.domains:
            if domain.tls_enabled:
                tls_group_by_secret_name[domain.tls_secret_name].append(domain.host)

        tls = []
        for secret_name, hosts in tls_group_by_secret_name.items():
            tls.append({"hosts": hosts, "secretName": secret_name})

        rules = []
        for domain in obj.domains:
            paths = []
            for backend in domain.path_backends:
                paths.append(
                    {
                        "path": (
                            nginx_adaptor.make_location_path(backend.path_prefix or "/")
                            if obj.rewrite_to_root
                            else backend.path_prefix
                        ),
                        "pathType": "ImplementationSpecific",
                        "backend": {
                            "service": {
                                "name": backend.service_name,
                                "port": {
                                    "name": backend.service_port_name,
                                },
                            },
                        },
                    }
                )
            rules.append({"host": domain.host, "http": {"paths": paths}})

        body: Dict[str, Any] = {
            "apiVersion": self.get_api_version_from_gvk(self.gvk_config),
            "kind": "Ingress",
            "metadata": {
                "name": obj.name,
                "annotations": annotations,
                "labels": {"env": "dev"},
            },
            "spec": {"rules": rules, "tls": tls},
        }

        if original_obj:
            body["metadata"]["resourceVersion"] = original_obj.metadata.resourceVersion

        return body


class DevSandboxIngressDeserializer(AppEntityDeserializer["DevSandboxIngress", "WlApp"]):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "DevSandboxIngress":
        spec = kube_data.spec
        rules = spec.get("rules") or []
        tls = spec.get("tls") or []
        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            domains=self._parse_ingress_domains(rules, tls),
        )

    def _parse_ingress_domains(
        self, rules: List[ResourceInstance], tls: List[ResourceInstance]
    ) -> List[IngressDomain]:
        domains: List[IngressDomain] = []

        host_secret_map = {}
        for ingress_tls in tls:
            for host in ingress_tls.hosts:
                host_secret_map[host] = ingress_tls.get("secretName", "")

        for rule in rules:
            if not rule.get("http"):
                continue

            domains.append(
                IngressDomain(
                    host=rule.host,
                    tls_enabled=(rule.host in host_secret_map),
                    tls_secret_name=host_secret_map.get(rule.host, ""),
                    path_backends=self._parse_backends(rule.http.paths),
                )
            )

        return domains

    def _parse_backends(self, paths: List[ResourceInstance]) -> List[IngressPathBackend]:
        nginx_adaptor = NginxRegexRewrittenProvider()

        backends: List[IngressPathBackend] = []
        for ingress_path in paths:
            if not ingress_path.backend.get("service"):
                continue

            if not (service_port_name := ingress_path.backend.service.port.name):
                raise ValueError(f"Only support ingress with port name, detail: {ingress_path.backend}")

            backends.append(
                IngressPathBackend(
                    path_prefix=nginx_adaptor.parse_location_path(ingress_path.path),
                    service_name=ingress_path.backend.service.name,
                    service_port_name=service_port_name,
                )
            )

        if not backends:
            raise ValueError("No ingress backend can be found in ingress rules")

        return backends
