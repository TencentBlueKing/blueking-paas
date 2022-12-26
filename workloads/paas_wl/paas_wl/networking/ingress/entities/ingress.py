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
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from kubernetes.dynamic import ResourceInstance

from paas_wl.cluster.constants import ClusterFeatureFlag
from paas_wl.cluster.models import Cluster
from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.ingress.entities.utils import NginxPatternAdaptor
from paas_wl.platform.applications.models import App
from paas_wl.resources.base import kres
from paas_wl.resources.kube_res.base import AppEntity, AppEntityDeserializer, AppEntityManager, AppEntitySerializer

ANNOT_SERVER_SNIPPET = 'nginx.ingress.kubernetes.io/server-snippet'
ANNOT_CONFIGURATION_SNIPPET = 'nginx.ingress.kubernetes.io/configuration-snippet'
ANNOT_REWRITE_TARGET = "nginx.ingress.kubernetes.io/rewrite-target"
ANNOT_SSL_REDIRECT = 'nginx.ingress.kubernetes.io/ssl-redirect'

# Annotations managed by system
reserved_annotations = {ANNOT_SERVER_SNIPPET, ANNOT_CONFIGURATION_SNIPPET, ANNOT_REWRITE_TARGET, ANNOT_SSL_REDIRECT}


logger = logging.getLogger(__name__)


class IngressNginxAdaptor:
    """An Adaptor shield different versions of the ingress-nginx-controller implementation"""

    def __init__(self, cluster: "Cluster", force_use_pattern: bool = False):
        self.cluster = cluster
        use_pattern = self.cluster.has_feature_flag(ClusterFeatureFlag.INGRESS_USE_PATTERN)
        if force_use_pattern:
            use_pattern = True
        self.use_pattern = use_pattern

    def make_configuration_snippet(self, fallback_script_name: Optional[str] = '') -> str:
        """Make configuration snippet which set X-Script-Name as the sub-path provided from platform or custom domain

        Must use "configuration-snippet" instead of "server-snippet" otherwise "proxy-set-header"
        directive will stop working because it already can be found in location block.
        """
        if not self.use_pattern:
            # `$location_path` was a variable set by ingress-controller which lives in `location` block ,
            # it's value equals `rules.https?.paths[].path` in the ingress's specification, we will use it
            # as the `Script-Name` for application.
            #
            # Which means while a domain might have many different paths, the `Script-Name` will always
            # be determined by the requests path. For example:
            #
            # - when user requests '/prod--default--foo/something', which matches `/prod--default--foo/` location,
            #   the `X-Script-Name` would be set to `/prod--default--foo/`
            # - when user requests '/foo/something', which matches `/foo/` location, `X-Script-Name` will be `/foo/`
            #
            # However, `$location_path` was added in version 0.16.0
            # For forward compatibility, we should set $location_path to shortest_path as fallback.
            # To know "How the fallback work", see also: [nginx-variables-variable-scope](https://openresty.org/download/agentzh-nginx-tutorials-en.html#nginx-variables-variable-scope)  # noqa

            snippet = dedent(
                f"""\
            if ($location_path = '') {{
                set $location_path "{fallback_script_name}";
            }}

            proxy_set_header X-Script-Name $location_path;
            """
            )
            return snippet

        return NginxPatternAdaptor().make_configuration_snippet()

    def build_http_path(self, path_str: str) -> str:
        """build the http path, which is compatible with `rewrite-target` for all version nginx-ingress-controller

        To be compatible with `rewrite-target` nginx-ingress-controller >=0.22, the http path should be a pattern
        Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
        """
        if not self.use_pattern:
            if not settings.APP_INGRESS_EXT_V1BETA1_PATH_TRAILING_SLASH:
                path_str = path_str.rstrip("/")
            return path_str
        return NginxPatternAdaptor.make_location_path(path_str)

    def build_rewrite_target(self) -> str:
        """build the rewrite target which will rewrite all request to sub-path provided from platform or custom domain

        In Version 0.22.0 +, any substrings within the request URI that need to be passed to the rewritten path
        must explicitly be defined in a capture group.
        Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
        """
        if not self.use_pattern:
            return "/"
        return NginxPatternAdaptor.make_rewrite_target()

    def parse_http_path(self, pattern_or_path: str) -> str:
        """parse path_str from path pattern(which is return by build_http_path)"""
        if not self.use_pattern:
            # not a pattern, return directly
            return pattern_or_path
        return NginxPatternAdaptor.parse_location_path(pattern_or_path)


class ConfigurationSnippetPatcher:
    START_MARK = "# WARNING: BLOCK FOR IngressNginxAdaptor BEGIN"
    END_MARK = "# WARNING: BLOCK FOR IngressNginxAdaptor END"
    _REGEX = re.compile(f"{START_MARK}.+?{END_MARK}")

    def patch(self, base: str, extend: str) -> str:
        """patch base configuration_snippet with extend if unpatched"""
        if not self._REGEX.findall(base, re.M | re.S):
            return "\n".join([base, self.START_MARK, extend, self.END_MARK])
        return base

    def unpatch(self, snippet: str) -> str:
        """reverse patch_configuration_snippet"""
        if self._REGEX.findall(snippet, re.M | re.S):
            return self._REGEX.sub("", snippet, re.M | re.S)
        return snippet


class IngressV1Beta1Serializer(AppEntitySerializer['ProcessIngress']):
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
            ANNOT_CONFIGURATION_SNIPPET: ConfigurationSnippetPatcher().patch(
                obj.configuration_snippet,
                nginx_adaptor.make_configuration_snippet(fallback_script_name=obj.domains[0].primary_prefix_path),
            ),
            # Disable HTTPS redirect by default, the behaviour might be overwritten in the future
            ANNOT_SSL_REDIRECT: "false",
            **obj.annotations,
        }
        if obj.rewrite_to_root:
            annotations[ANNOT_REWRITE_TARGET] = nginx_adaptor.build_rewrite_target()

        tls_group_by_secret_name: Dict[str, List] = defaultdict(list)
        for domain in obj.domains:
            if domain.tls_enabled:
                tls_group_by_secret_name[domain.tls_secret_name].append(domain.host)

        tls = []
        for secret_name, hosts in tls_group_by_secret_name.items():
            tls.append({'hosts': hosts, 'secretName': secret_name})

        rules = []
        for domain in obj.domains:
            paths = []
            for path_str in domain.path_prefix_list:
                paths.append(
                    {
                        "path": nginx_adaptor.build_http_path(path_str or '/') if obj.rewrite_to_root else path_str,
                        "backend": {"serviceName": obj.service_name, "servicePort": obj.service_port_name},
                    }
                )
            rules.append({'host': domain.host, 'http': {'paths': paths}})

        body: Dict[str, Any] = {
            'metadata': {
                'name': obj.name,
                'namespace': obj.app.namespace,
                'annotations': annotations,
            },
            'spec': {'rules': rules, 'tls': tls},
            'apiVersion': self.get_api_version_from_gvk(self.gvk_config),
            'kind': 'Ingress',
        }

        if original_obj:
            body['metadata']['resourceVersion'] = original_obj.metadata.resourceVersion
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

    def deserialize(self, app: App, kube_data: ResourceInstance) -> "ProcessIngress":
        nginx_adaptor = IngressNginxAdaptor(get_cluster_by_app(app))
        spec = kube_data.spec
        rules = spec.get("rules") or []
        service_name, service_port_name = self.parse_service_info_from_rules(rules)
        all_annotations = kube_data.metadata.annotations or {}
        extra_annotations = {k: v for k, v in all_annotations.items() if k not in reserved_annotations}

        return ProcessIngress(
            app=app,
            name=kube_data.metadata.name,
            domains=self.parse_domains(spec.get("rules") or [], spec.get("tls") or [], nginx_adaptor=nginx_adaptor),
            service_name=service_name,
            service_port_name=service_port_name,
            server_snippet=all_annotations.get(ANNOT_SERVER_SNIPPET, ""),
            configuration_snippet=ConfigurationSnippetPatcher().unpatch(
                all_annotations.get(ANNOT_CONFIGURATION_SNIPPET, "")
            ),
            rewrite_to_root=ANNOT_REWRITE_TARGET in all_annotations.keys(),
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
                host_secret_map[host] = ingress_tls.get('secretName', '')

        for rule in rules:
            if not rule.get("http"):
                continue
            domains.append(
                PIngressDomain(
                    host=rule.host,
                    tls_enabled=(rule.host in host_secret_map),
                    tls_secret_name=host_secret_map.get(rule.host, ''),
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
            raise ValueError('No ingress backend can be found in ingress rules')
        elif len(svc_info_pairs) != 1:
            raise ValueError(f'different backends found: {svc_info_pairs}')
        return svc_info_pairs.pop()


class IngressV1Serializer(AppEntitySerializer["ProcessIngress"]):
    """Serializer for ProcessIngress in ApiVersion networking.k8s.io/v1, which is available in k8s 1.19+

    IMPORTANT: This class is not compatible with ingress-nginx < 1.0
    Ref: https://kubernetes.github.io/ingress-nginx/deploy/#running-on-kubernetes-versions-older-than-119
    """

    @staticmethod
    def get_api_version_from_gvk(gvk_config):
        # 虽然不用正则表达式下发 Ingress 不会有问题, 但是将无法保证 rewrite-target/X-Script-Name 等逻辑
        # 因此在 ENABLE_MODERN_INGRESS_SUPPORT 未打开时禁用对 networking.k8s.io/v1 的支持
        if not settings.ENABLE_MODERN_INGRESS_SUPPORT:
            return "unsupported"
        return "networking.k8s.io/v1"

    def serialize(self, obj: "ProcessIngress", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        """serialize obj into Ingress(networking.k8s.io/v1)"""
        nginx_adaptor = IngressNginxAdaptor(get_cluster_by_app(obj.app), force_use_pattern=True)
        annotations = {
            ANNOT_SERVER_SNIPPET: obj.server_snippet,
            ANNOT_CONFIGURATION_SNIPPET: ConfigurationSnippetPatcher().patch(
                obj.configuration_snippet,
                nginx_adaptor.make_configuration_snippet(fallback_script_name=obj.domains[0].primary_prefix_path),
            ),
            # Disable HTTPS redirect by default, the behaviour might be overwritten in the future
            ANNOT_SSL_REDIRECT: "false",
            **obj.annotations,
        }
        if obj.rewrite_to_root:
            annotations[ANNOT_REWRITE_TARGET] = nginx_adaptor.build_rewrite_target()

        tls_group_by_secret_name: Dict[str, List] = defaultdict(list)
        for domain in obj.domains:
            if domain.tls_enabled:
                tls_group_by_secret_name[domain.tls_secret_name].append(domain.host)

        tls = []
        for secret_name, hosts in tls_group_by_secret_name.items():
            tls.append({'hosts': hosts, 'secretName': secret_name})

        rules = []
        for domain in obj.domains:
            paths = []
            for path_str in domain.path_prefix_list:
                paths.append(
                    {
                        "path": nginx_adaptor.build_http_path(path_str or '/') if obj.rewrite_to_root else path_str,
                        "pathType": "ImplementationSpecific",
                        "backend": {
                            "service": {"name": obj.service_name, "port": {"name": obj.service_port_name}},
                        },
                    }
                )
            rules.append({'host': domain.host, 'http': {'paths': paths}})

        body: Dict[str, Any] = {
            'metadata': {
                'name': obj.name,
                'namespace': obj.app.namespace,
                'annotations': annotations,
            },
            'spec': {'rules': rules, 'tls': tls},
            'apiVersion': self.get_api_version_from_gvk(self.gvk_config),
            'kind': 'Ingress',
        }

        if original_obj:
            body['metadata']['resourceVersion'] = original_obj.metadata.resourceVersion
        return body


class IngressV1Deserializer(AppEntityDeserializer["ProcessIngress"]):
    """Deserializer for ProcessIngress in ApiVersion networking.k8s.io/v1, which is available in k8s 1.19+

    IMPORTANT: This class is not compatible with ingress-nginx < 1.0
    Ref: https://kubernetes.github.io/ingress-nginx/deploy/#running-on-kubernetes-versions-older-than-119
    """

    @staticmethod
    def get_api_version_from_gvk(gvk_config):
        # 虽然不用正则表达式下发 Ingress 不会有问题, 但是将无法保证 rewrite-target/X-Script-Name 等逻辑
        # 因此在 ENABLE_MODERN_INGRESS_SUPPORT 未打开时禁用对 networking.k8s.io/v1 的支持
        if not settings.ENABLE_MODERN_INGRESS_SUPPORT:
            return "unsupported"
        return "networking.k8s.io/v1"

    def deserialize(self, app: App, kube_data: ResourceInstance) -> "ProcessIngress":
        nginx_adaptor = IngressNginxAdaptor(get_cluster_by_app(app), force_use_pattern=True)
        spec = kube_data.spec
        rules = spec.get("rules") or []
        service_name, service_port_name = self.parse_service_info_from_rules(rules)
        all_annotations = kube_data.metadata.annotations or {}
        extra_annotations = {k: v for k, v in all_annotations.items() if k not in reserved_annotations}

        return ProcessIngress(
            app=app,
            name=kube_data.metadata.name,
            domains=self.parse_domains(rules or [], spec.get("tls") or [], nginx_adaptor=nginx_adaptor),
            service_name=service_name,
            service_port_name=service_port_name,
            server_snippet=all_annotations.get(ANNOT_SERVER_SNIPPET, ""),
            configuration_snippet=ConfigurationSnippetPatcher().unpatch(
                all_annotations.get(ANNOT_CONFIGURATION_SNIPPET, "")
            ),
            rewrite_to_root=ANNOT_REWRITE_TARGET in all_annotations.keys(),
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
                host_secret_map[host] = ingress_tls.get('secretName', '')

        for rule in rules:
            if not rule.get("http"):
                continue
            domains.append(
                PIngressDomain(
                    host=rule.host,
                    tls_enabled=(rule.host in host_secret_map),
                    tls_secret_name=host_secret_map.get(rule.host, ''),
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
                if not ingress_path.backend.get("service"):
                    continue
                service_name = ingress_path.backend.service.name
                service_port_name = ingress_path.backend.service.port.name
                if not service_port_name:
                    raise ValueError(f'Only support ingress with port name, detail: {ingress_path.backend}')
                svc_info_pairs.add((service_name, service_port_name))

        if not svc_info_pairs:
            raise ValueError('No ingress backend can be found in ingress rules')
        elif len(svc_info_pairs) != 1:
            raise ValueError(f'different backends found: {svc_info_pairs}')
        return svc_info_pairs.pop()


@dataclass
class PIngressDomain:
    """Ingress Domain object

    :param path_prefix_list: Accessable paths for current domain, default value: ['/']
    """

    host: str

    tls_enabled: bool = False
    tls_secret_name: str = ''
    path_prefix_list: List[str] = field(default_factory=lambda: ['/'])

    @property
    def primary_prefix_path(self) -> str:
        return self.path_prefix_list[0]


@dataclass
class ProcessIngress(AppEntity):
    """Ingress object for process, external service

    :param annotations: extra annotations
    """

    domains: List[PIngressDomain]
    service_name: str
    service_port_name: str

    server_snippet: str = ''
    configuration_snippet: str = ''

    # Whether to rewrite path to "/" when request matches path pattern, for example:
    # when path pattern is "/foo/" and user is requesting "/foo/bar", the path will be rewritten
    # to "/bar" if `rewrite_to_root`` is True.
    rewrite_to_root: bool = False
    annotations: Dict = field(default_factory=dict)

    class Meta:
        kres_class = kres.KIngress
        deserializers = [
            IngressV1Beta1Deserializer,
            IngressV1Deserializer,
        ]
        serializers = [
            IngressV1Beta1Serializer,
            IngressV1Serializer,
        ]


ingress_kmodel: AppEntityManager[ProcessIngress] = AppEntityManager[ProcessIngress](ProcessIngress)
