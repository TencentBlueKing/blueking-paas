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
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.utils.functional import lazy
from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import (
    AppEntity,
    AppEntityDeserializer,
    AppEntityManager,
    AppEntitySerializer,
)
from paas_wl.workloads.networking.ingress.kres_entities.utils import (
    LegacyNginxRewrittenProvider,
    NginxRegexRewrittenProvider,
)

ANNOT_SERVER_SNIPPET = "nginx.ingress.kubernetes.io/server-snippet"
ANNOT_CONFIGURATION_SNIPPET = "nginx.ingress.kubernetes.io/configuration-snippet"
ANNOT_REWRITE_TARGET = "nginx.ingress.kubernetes.io/rewrite-target"
ANNOT_SSL_REDIRECT = "nginx.ingress.kubernetes.io/ssl-redirect"
# 由于 tke 集群默认会为没有绑定 CLB 的 Ingress 创建并绑定公网 CLB 的危险行为，
# bcs-webhook 会对下发/更新配置时没有指定 clb 的 Ingress 进行拦截，在关闭 tke 集群的 l7-lb-controller 组件后
# 可以在下发 Ingress 时候添加注解 bkbcs.tencent.com/skip-filter-clb: "true" 以跳过 bcs-webhook 的拦截
# l7-lb-controller 状态查询：kubectl get deploy l7-lb-controller -n kube-system
ANNOT_SKIP_FILTER_CLB = "bkbcs.tencent.com/skip-filter-clb"

# Annotations managed by system
reserved_annotations = {
    ANNOT_SERVER_SNIPPET,
    ANNOT_CONFIGURATION_SNIPPET,
    ANNOT_REWRITE_TARGET,
    ANNOT_SSL_REDIRECT,
    ANNOT_SKIP_FILTER_CLB,
}


logger = logging.getLogger(__name__)


class IngressNginxAdaptor:
    """An Adaptor shield different versions(0.20.0 ~ 0.51.0) of the ingress-nginx-controller implementation
    Note: IngressNginxAdaptor only work for Ingress api version in ["extensions/v1beta1", "networking.k8s.io/v1beta1"]

    :param cluster: The k8s cluster where the ingress will be applied to
    """

    def __init__(self, cluster: "Cluster"):
        self.cluster = cluster
        self.use_regex = self.cluster.has_feature_flag(ClusterFeatureFlag.INGRESS_USE_REGEX)

    def make_configuration_snippet(self, fallback_script_name: Optional[str] = "") -> str:
        """Make configuration snippet which set X-Script-Name as the sub-path provided by platform or custom domain

        Must use "configuration-snippet" instead of "server-snippet" otherwise "proxy-set-header"
        directive will stop working because it already can be found in location block.
        """
        if not self.use_regex:
            return LegacyNginxRewrittenProvider().make_configuration_snippet(fallback_script_name)
        return NginxRegexRewrittenProvider().make_configuration_snippet()

    def build_http_path(self, path_str: str) -> str:
        """build the http path, which is compatible with `rewrite-target` for all version nginx-ingress-controller

        To be compatible with `rewrite-target` nginx-ingress-controller >=0.22, the http path should be a pattern
        Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
        """
        if not self.use_regex:
            return LegacyNginxRewrittenProvider().make_location_path(path_str)
        return NginxRegexRewrittenProvider().make_location_path(path_str)

    def build_rewrite_target(self) -> str:
        """build the rewrite target which will rewrite all request to sub-path provided by platform or custom domain

        In Version 0.22.0 +, any substrings within the request URI that need to be passed to the rewritten path
        must explicitly be defined in a capture group.
        Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
        """
        if not self.use_regex:
            return LegacyNginxRewrittenProvider().make_rewrite_target()
        return NginxRegexRewrittenProvider().make_rewrite_target()

    def parse_http_path(self, pattern_or_path: str) -> str:
        """parse path_str from path pattern(which is return by build_http_path)"""
        if not self.use_regex:
            return LegacyNginxRewrittenProvider().parse_location_path(pattern_or_path)
        return NginxRegexRewrittenProvider().parse_location_path(pattern_or_path)


class ConfigurationSnippetPatcher:
    START_MARK = "# WARNING: BLOCK FOR IngressNginxAdaptor BEGIN"
    END_MARK = "# WARNING: BLOCK FOR IngressNginxAdaptor END"
    REGEX = f"{START_MARK}.+?{END_MARK}"

    @dataclass
    class PatchResult:
        """
        :param changed: whether the given configuration_snippet is changed by ConfigurationSnippetPatcher
        :param configuration_snippet: the new(or unchanged if changed is False) configuration_snippet
        """

        changed: bool
        configuration_snippet: str

    def patch(self, base: str, extend: str) -> PatchResult:
        """patch base configuration_snippet with extend if unpatched

        :return: PatchResult
        """
        if not re.findall(self.REGEX, base, re.M | re.S):
            return self.PatchResult(True, "\n".join([base, self.START_MARK, extend, self.END_MARK]))
        return self.PatchResult(False, base)

    def unpatch(self, snippet: str) -> PatchResult:
        """reverse patch_configuration_snippet

        :return: PatchResult
        """
        if re.findall(self.REGEX, snippet, re.M | re.S):
            return self.PatchResult(True, re.sub(self.REGEX, "", snippet, count=0, flags=re.M | re.S).strip())
        return self.PatchResult(False, snippet)


class IngressV1Beta1Serializer(AppEntitySerializer["ProcessIngress"]):
    """Serializer for ProcessIngress in ApiVersion networking.k8s.io/v1beta1 or extensions/v1beta1

    IMPORTANT: This class is not compatible with ingress-nginx >= 1.0
    Ref: https://kubernetes.github.io/ingress-nginx/deploy/#running-on-kubernetes-versions-older-than-119
    """

    @staticmethod
    def get_api_version_from_gvk(gvk_config):
        """
        Model Ingress(networking.k8s.io/v1beta1) and Ingress(extensions/v1beta1) have same structure.
        Ref: https://github.com/kubernetes/kubernetes/pull/74057
        """
        # networking.k8s.io/v1beta1 is available since k8s v1.14, and is unavailable since k8s 1.22+
        # Ref: https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.14.md?plain=1#L1001
        if "networking.k8s.io/v1beta1" in gvk_config.available_apiversions:
            return "networking.k8s.io/v1beta1"
        return "extensions/v1beta1"

    def serialize(self, obj: "ProcessIngress", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        """serialize obj into Ingress(networking.k8s.io/v1beta1)"""
        nginx_adaptor = IngressNginxAdaptor(get_cluster_by_app(obj.app))
        annotations = {
            ANNOT_SERVER_SNIPPET: obj.server_snippet,
            ANNOT_CONFIGURATION_SNIPPET: obj.configuration_snippet,
            # Disable HTTPS redirect by default, the behaviour might be overwritten in the future
            ANNOT_SSL_REDIRECT: "false",
            ANNOT_SKIP_FILTER_CLB: "true",
            **obj.annotations,
        }
        if obj.rewrite_to_root:
            annotations[ANNOT_REWRITE_TARGET] = nginx_adaptor.build_rewrite_target()
        if obj.set_header_x_script_name:
            annotations[ANNOT_CONFIGURATION_SNIPPET] = (
                ConfigurationSnippetPatcher()
                .patch(
                    obj.configuration_snippet,
                    nginx_adaptor.make_configuration_snippet(fallback_script_name=obj.domains[0].primary_prefix_path),
                )
                .configuration_snippet
            )

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
            for path_str in domain.path_prefix_list:
                paths.append(
                    {
                        "path": nginx_adaptor.build_http_path(path_str or "/") if obj.rewrite_to_root else path_str,
                        "backend": {"serviceName": obj.service_name, "servicePort": obj.service_port_name},
                    }
                )
            rules.append({"host": domain.host, "http": {"paths": paths}})

        body: Dict[str, Any] = {
            "metadata": {
                "name": obj.name,
                "namespace": obj.app.namespace,
                "annotations": annotations,
            },
            "spec": {"rules": rules, "tls": tls},
            "apiVersion": self.get_api_version_from_gvk(self.gvk_config),
            "kind": "Ingress",
        }

        if original_obj:
            body["metadata"]["resourceVersion"] = original_obj.metadata.resourceVersion
        return body


class IngressV1Beta1Deserializer(AppEntityDeserializer["ProcessIngress"]):
    """Deserializer for ProcessIngress in ApiVersion networking.k8s.io/v1beta1 or extensions/v1beta1

    IMPORTANT: This class is not compatible with ingress-nginx >= 1.0
    Ref: https://kubernetes.github.io/ingress-nginx/deploy/#running-on-kubernetes-versions-older-than-119
    """

    @staticmethod
    def get_api_version_from_gvk(gvk_config):
        """
        Model Ingress(networking.k8s.io/v1beta1) and Ingress(extensions/v1beta1) have same structure.
        Ref: https://github.com/kubernetes/kubernetes/pull/74057
        """
        # networking.k8s.io/v1beta1 is available since k8s v1.14
        # Ref: https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.14.md?plain=1#L1001
        if "networking.k8s.io/v1beta1" in gvk_config.available_apiversions:
            return "networking.k8s.io/v1beta1"
        return "extensions/v1beta1"

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "ProcessIngress":
        nginx_adaptor = IngressNginxAdaptor(get_cluster_by_app(app))
        spec = kube_data.spec
        rules = spec.get("rules") or []
        service_name, service_port_name = self.parse_service_info_from_rules(rules)
        all_annotations = kube_data.metadata.annotations.__dict__ or {}
        extra_annotations = {k: v for k, v in all_annotations.items() if k not in reserved_annotations}

        configuration_snippet = all_annotations.get(ANNOT_CONFIGURATION_SNIPPET, "")
        # check whether set x-script-name http header in configuration_snippet
        set_header_x_script_name = "proxy_set_header X-Script-Name" in configuration_snippet
        return ProcessIngress(
            app=app,
            name=kube_data.metadata.name,
            domains=self.parse_domains(spec.get("rules") or [], spec.get("tls") or [], nginx_adaptor=nginx_adaptor),
            service_name=service_name,
            service_port_name=service_port_name,
            server_snippet=all_annotations.get(ANNOT_SERVER_SNIPPET, ""),
            configuration_snippet=ConfigurationSnippetPatcher().unpatch(configuration_snippet).configuration_snippet,
            rewrite_to_root=ANNOT_REWRITE_TARGET in all_annotations,
            set_header_x_script_name=set_header_x_script_name,
            annotations=extra_annotations,
        )

    def parse_domains(
        self, rules: List[ResourceInstance], tls: List[ResourceInstance], nginx_adaptor: IngressNginxAdaptor
    ) -> List["PIngressDomain"]:
        """parse PIngressDomain from given rules and tls"""
        domains = []
        # Analyze TLS section first
        host_secret_map = {}
        for ingress_tls in tls:
            for host in ingress_tls.hosts:
                host_secret_map[host] = ingress_tls.get("secretName", "")

        for rule in rules:
            if not rule.get("http"):
                continue
            domains.append(
                PIngressDomain(
                    host=rule.host,
                    tls_enabled=(rule.host in host_secret_map),
                    tls_secret_name=host_secret_map.get(rule.host, ""),
                    path_prefix_list=[
                        nginx_adaptor.parse_http_path(ingress_path.path) for ingress_path in rule.http.paths
                    ],
                )
            )
        return domains

    def parse_service_info_from_rules(self, rules: List[ResourceInstance]) -> Tuple[str, str]:
        """parse Tuple[service_name, service_port_name] from List[IngressRule]

        :raise ValueError: if not ingress backend can be found or different backends found
        """
        svc_info_pairs = set()
        for rule in rules:
            if not rule.get("http"):
                continue
            for ingress_path in rule.http.paths:
                svc_info_pairs.add((ingress_path.backend.serviceName, ingress_path.backend.servicePort))

        if not svc_info_pairs:
            raise ValueError("No ingress backend can be found in ingress rules")
        elif len(svc_info_pairs) != 1:
            raise ValueError(f"different backends found: {svc_info_pairs}")
        return svc_info_pairs.pop()


class IngressV1Serializer(AppEntitySerializer["ProcessIngress"]):
    """Serializer for ProcessIngress in ApiVersion networking.k8s.io/v1, which is available in k8s 1.19+

    IMPORTANT: This class is not compatible with ingress-nginx < 1.0
    Ref: https://kubernetes.github.io/ingress-nginx/deploy/#running-on-kubernetes-versions-older-than-119
    """

    @staticmethod
    def get_api_version_from_gvk(gvk_config):
        return "networking.k8s.io/v1"

    def serialize(self, obj: "ProcessIngress", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        """serialize obj into Ingress(networking.k8s.io/v1)"""
        nginx_adaptor = NginxRegexRewrittenProvider()
        annotations = {
            ANNOT_SERVER_SNIPPET: obj.server_snippet,
            ANNOT_CONFIGURATION_SNIPPET: obj.configuration_snippet,
            # Disable HTTPS redirect by default, the behaviour might be overwritten in the future
            ANNOT_SSL_REDIRECT: "false",
            ANNOT_SKIP_FILTER_CLB: "true",
            **obj.annotations,
        }
        if obj.rewrite_to_root:
            annotations[ANNOT_REWRITE_TARGET] = nginx_adaptor.make_rewrite_target()
        if obj.set_header_x_script_name:
            annotations[ANNOT_CONFIGURATION_SNIPPET] = (
                ConfigurationSnippetPatcher()
                .patch(
                    obj.configuration_snippet,
                    nginx_adaptor.make_configuration_snippet(),
                )
                .configuration_snippet
            )

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
            for path_str in domain.path_prefix_list:
                paths.append(
                    {
                        "path": nginx_adaptor.make_location_path(path_str or "/") if obj.rewrite_to_root else path_str,
                        "pathType": "ImplementationSpecific",
                        "backend": {
                            "service": {"name": obj.service_name, "port": {"name": obj.service_port_name}},
                        },
                    }
                )
            rules.append({"host": domain.host, "http": {"paths": paths}})

        body: Dict[str, Any] = {
            "metadata": {
                "name": obj.name,
                "namespace": obj.app.namespace,
                "annotations": annotations,
            },
            "spec": {"rules": rules, "tls": tls},
            "apiVersion": self.get_api_version_from_gvk(self.gvk_config),
            "kind": "Ingress",
        }

        if original_obj:
            body["metadata"]["resourceVersion"] = original_obj.metadata.resourceVersion
        return body


class IngressV1Deserializer(AppEntityDeserializer["ProcessIngress"]):
    """Deserializer for ProcessIngress in ApiVersion networking.k8s.io/v1, which is available in k8s 1.19+

    IMPORTANT: This class is not compatible with ingress-nginx < 1.0
    Ref: https://kubernetes.github.io/ingress-nginx/deploy/#running-on-kubernetes-versions-older-than-119
    """

    @staticmethod
    def get_api_version_from_gvk(gvk_config):
        return "networking.k8s.io/v1"

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "ProcessIngress":
        spec = kube_data.spec
        rules = spec.get("rules") or []
        service_name, service_port_name = self.parse_service_info_from_rules(rules)
        all_annotations = kube_data.metadata.annotations.__dict__ or {}
        extra_annotations = {k: v for k, v in all_annotations.items() if k not in reserved_annotations}

        configuration_snippet = all_annotations.get(ANNOT_CONFIGURATION_SNIPPET, "")
        # check whether set x-script-name http header in configuration_snippet
        set_header_x_script_name = "proxy_set_header X-Script-Name" in configuration_snippet
        return ProcessIngress(
            app=app,
            name=kube_data.metadata.name,
            domains=self.parse_domains(rules or [], spec.get("tls") or []),
            service_name=service_name,
            service_port_name=service_port_name,
            server_snippet=all_annotations.get(ANNOT_SERVER_SNIPPET, ""),
            configuration_snippet=ConfigurationSnippetPatcher().unpatch(configuration_snippet).configuration_snippet,
            rewrite_to_root=ANNOT_REWRITE_TARGET in all_annotations,
            set_header_x_script_name=set_header_x_script_name,
            annotations=extra_annotations,
        )

    def parse_domains(self, rules: List[ResourceInstance], tls: List[ResourceInstance]) -> List["PIngressDomain"]:
        """parse PIngressDomain from given rules and tls"""
        nginx_adaptor = NginxRegexRewrittenProvider()
        domains = []
        # Analyze TLS section first
        host_secret_map = {}
        for ingress_tls in tls:
            for host in ingress_tls.hosts:
                host_secret_map[host] = ingress_tls.get("secretName", "")

        for rule in rules:
            if not rule.get("http"):
                continue
            domains.append(
                PIngressDomain(
                    host=rule.host,
                    tls_enabled=(rule.host in host_secret_map),
                    tls_secret_name=host_secret_map.get(rule.host, ""),
                    path_prefix_list=[
                        nginx_adaptor.parse_location_path(ingress_path.path) for ingress_path in rule.http.paths
                    ],
                )
            )
        return domains

    def parse_service_info_from_rules(self, rules: List[ResourceInstance]) -> Tuple[str, str]:
        """parse Tuple[service_name, service_port_name] from List[IngressRule]

        :raise ValueError: if not ingress backend can be found or different backends found
        """
        svc_info_pairs = set()
        for rule in rules:
            if not rule.get("http"):
                continue
            for ingress_path in rule.http.paths:
                if not ingress_path.backend.get("service"):
                    continue
                service_name = ingress_path.backend.service.name
                service_port_name = ingress_path.backend.service.port.name
                if not service_port_name:
                    raise ValueError(f"Only support ingress with port name, detail: {ingress_path.backend}")
                svc_info_pairs.add((service_name, service_port_name))

        if not svc_info_pairs:
            raise ValueError("No ingress backend can be found in ingress rules")
        elif len(svc_info_pairs) != 1:
            raise ValueError(f"different backends found: {svc_info_pairs}")
        return svc_info_pairs.pop()


@dataclass
class PIngressDomain:
    """Ingress Domain object

    :param path_prefix_list: Accessable paths for current domain, default value: ['/']
    """

    host: str

    tls_enabled: bool = False
    tls_secret_name: str = ""
    path_prefix_list: List[str] = field(default_factory=lambda: ["/"])

    @property
    def primary_prefix_path(self) -> str:
        return self.path_prefix_list[0]


def make_serializers():
    if not settings.ENABLE_MODERN_INGRESS_SUPPORT:
        return [IngressV1Beta1Serializer]
    return [
        IngressV1Beta1Serializer,
        IngressV1Serializer,
    ]


def make_deserializers():
    if not settings.ENABLE_MODERN_INGRESS_SUPPORT:
        return [IngressV1Beta1Deserializer]
    return [
        IngressV1Beta1Deserializer,
        IngressV1Deserializer,
    ]


@dataclass
class ProcessIngress(AppEntity):
    """Ingress object for process, external service

    :param annotations: extra annotations
    """

    domains: List[PIngressDomain]
    service_name: str
    service_port_name: str

    server_snippet: str = ""
    configuration_snippet: str = ""

    # Whether to rewrite path to "/" when request matches path pattern, for example:
    # when path pattern is "/foo/" and user is requesting "/foo/bar", the path will be rewritten
    # to "/bar" if `rewrite_to_root`` is True.
    rewrite_to_root: bool = False

    # Whether to set http header `X-Script-Name` to all request,
    # which means the sub-path provided by platform or custom domain
    # This config should always bo True, except those ingresses managed by `LegacyAppIngressMgr`
    set_header_x_script_name: bool = True
    annotations: Dict = field(default_factory=dict)

    class Meta:
        kres_class = kres.KIngress
        serializers = lazy(make_serializers, list)()
        deserializers = lazy(make_deserializers, list)()


ingress_kmodel: AppEntityManager[ProcessIngress] = AppEntityManager[ProcessIngress](ProcessIngress)
