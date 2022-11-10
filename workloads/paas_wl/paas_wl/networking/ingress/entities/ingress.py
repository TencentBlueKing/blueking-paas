# -*- coding: utf-8 -*-
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from django.conf import settings

from paas_wl.networking.ingress.constants import DomainsStructureType
from paas_wl.platform.applications.models import App
from paas_wl.resources.base import kres
from paas_wl.resources.kube_res.base import AppEntity, AppEntityDeserializer, AppEntityManager, AppEntitySerializer

ANNOT_SERVER_SNIPPET = 'nginx.ingress.kubernetes.io/server-snippet'
ANNOT_CONFIGURATION_SNIPPET = 'nginx.ingress.kubernetes.io/configuration-snippet'
ANNOT_REWRITE_TARGET = "nginx.ingress.kubernetes.io/rewrite-target"
ANNOT_SSL_REDIRECT = 'nginx.ingress.kubernetes.io/ssl-redirect'

# Annotations managed by systeam
reserved_annotations = {ANNOT_SERVER_SNIPPET, ANNOT_CONFIGURATION_SNIPPET, ANNOT_REWRITE_TARGET, ANNOT_SSL_REDIRECT}


class ProcessIngressSerializerMixin:
    api_version: str

    def get_rewrite_to_root_annots(self, ingress: "ProcessIngress") -> Dict:
        """get rewrite target pattern"""
        return {}

    def get_annotations(self, ingress: "ProcessIngress") -> Dict:
        """get annotations that applied to Ingress"""
        annotations = {
            ANNOT_SERVER_SNIPPET: ingress.server_snippet,
            ANNOT_CONFIGURATION_SNIPPET: ingress.configuration_snippet,
            **ingress.annotations,
        }

        if ingress.rewrite_to_root:
            annotations.update(self.get_rewrite_to_root_annots(ingress))

        # Disable HTTPS redirect by default, the behaviour might be overwritten in the future
        annotations.setdefault(ANNOT_SSL_REDIRECT, "false")
        return annotations

    def get_http_path(self, ingress: "ProcessIngress", path_str: str) -> Dict:
        """get path forwarding prefix"""
        raise NotImplementedError

    def get_declaration(self, ingress: "ProcessIngress", resourceVersion=None) -> Dict:
        """generate Kubernetes Ingress declaration"""
        tls_group_by_secret_name: Dict[str, List] = defaultdict(list)
        for domain in ingress.domains:
            if domain.tls_enabled:
                tls_group_by_secret_name[domain.tls_secret_name].append(domain.host)

        tls = []
        for secret_name, hosts in tls_group_by_secret_name.items():
            tls.append({'hosts': hosts, 'secretName': secret_name})

        rules = []
        for domain in ingress.domains:
            paths = []
            for path_str in domain.path_prefix_list:
                paths.append(self.get_http_path(ingress, path_str))
            rules.append({'host': domain.host, 'http': {'paths': paths}})

        body: Dict[str, Any] = {
            'metadata': {
                'name': ingress.name,
                'namespace': ingress.app.namespace,
                'annotations': self.get_annotations(ingress),
            },
            'spec': {'rules': rules, 'tls': tls},
            'apiVersion': self.api_version,
            'kind': 'Ingress',
        }

        if resourceVersion:
            body['metadata']['resourceVersion'] = resourceVersion

        return body


class ProcessIngressDeserializerMixin:
    api_version: str

    def get_http_path(self, path: str) -> str:
        """get the path prefix defined by the application"""
        return path

    def get_service(self, kube_data) -> Tuple[str, str]:
        """get the application defined service information"""
        services = set()
        for rule in kube_data.spec.rules:
            for path_obj in rule.http.paths:
                services.add(self.get_service_by_http_path(path_obj))

        if not services:
            raise ValueError('No ingress backend can be found in ingress rules')
        elif len(services) != 1:
            raise ValueError(f'different backends found: {services}')

        return services.pop()

    def get_annotations(self, kube_data):
        """get the application defined annotations"""
        if not kube_data.metadata.annotations:
            return {}
        return {k: v for k, v in kube_data.metadata.annotations.items() if k not in reserved_annotations}

    def get_rewrite_to_root(self, kube_data):
        """Whether the ingress was configured to rewrite path to root"""
        return False

    def get_process_ingress(self, app: App, kube_data) -> "ProcessIngress":
        """generate Process Ingress model"""
        service_name, service_port_name = self.get_service(kube_data)

        domains = []
        # Analyze TLS section first
        host_tls_map = {}
        for tls_rule in kube_data.spec.get('tls') or []:
            for host in tls_rule.hosts:
                host_tls_map[host] = tls_rule.get('secretName', '')

        # Only support single path rule ingress
        for rule in kube_data.spec.rules:
            domains.append(
                PIngressDomain(
                    host=rule.host,
                    tls_enabled=(rule.host in host_tls_map),
                    tls_secret_name=host_tls_map.get(rule.host, ''),
                    path_prefix_list=[self.get_http_path(obj.path) for obj in rule.http.paths],
                )
            )

        raw_annotations = kube_data.metadata.annotations or {}

        return ProcessIngress(
            name=kube_data.metadata.name,
            app=app,
            domains=domains,
            service_name=service_name,
            service_port_name=service_port_name,
            server_snippet=raw_annotations.get(ANNOT_SERVER_SNIPPET, ""),
            configuration_snippet=raw_annotations.get(ANNOT_CONFIGURATION_SNIPPET, ""),
            annotations=self.get_annotations(kube_data),
            rewrite_to_root=self.get_rewrite_to_root(kube_data),
        )

    def get_service_by_http_path(self, path) -> Tuple[str, str]:
        """get service information for the specified path"""
        raise NotImplementedError


class ProcessIngressSerializerExtV1beta1(ProcessIngressSerializerMixin, AppEntitySerializer['ProcessIngress']):
    """Serializer for ProcessIngress"""

    # k8s 1.8-1.12
    api_version = 'extensions/v1beta1'

    def get_http_path(self, ingress: "ProcessIngress", path_str: str) -> Dict:
        if not settings.APP_INGRESS_EXT_V1BETA1_PATH_TRAILING_SLASH:
            path_str = path_str.rstrip("/")

        return {
            "path": path_str,
            "backend": {"serviceName": ingress.service_name, "servicePort": ingress.service_port_name},
        }

    def get_rewrite_to_root_annots(self, ingress: "ProcessIngress") -> Dict:
        # **The `rewrite-target` is only compatible with ingress-nginx prior to 0.22.0**.
        # Below are some internal details:
        #
        # when the `rewrite-target` was configured to "/", ingress-nginx will generate below nginx
        # configurations:
        #
        #   rewrite "(?i)/sub-path/(.*)" /$1 break;
        #   rewrite "(?i)/sub-path/$" / break;
        #
        # The rule for generating these config lines is static, so make sure to avoid any regex "Capture groups"
        # ($1, $...) in `rewrite-target`.
        #
        # TODO: Decompose this logic from current Serializer class
        return {ANNOT_REWRITE_TARGET: "/"}

    def serialize(self, obj: AppEntity, original_obj=None, **kwargs) -> Dict:
        """Generate a kubernetes resource dict from ProcessIngress

        :param original_obj: if given, will update resource_version and other necessary fields
        """
        assert isinstance(obj, ProcessIngress), 'obj must be "ProcessIngress" type'
        resourceVersion = None
        if original_obj:
            resourceVersion = original_obj.metadata.resourceVersion

        return self.get_declaration(obj, resourceVersion)


class ProcessIngressDeserializerExtV1beta1(ProcessIngressDeserializerMixin, AppEntityDeserializer['ProcessIngress']):
    # k8s 1.8-1.12
    api_version = 'extensions/v1beta1'

    def get_http_path(self, path: str) -> str:
        """get the path prefix defined by the application"""

        if settings.APP_INGRESS_EXT_V1BETA1_PATH_TRAILING_SLASH and not path.endswith("/"):
            path = f"{path}/"

        return path

    def deserialize(self, app: App, kube_data) -> 'ProcessIngress':
        """Generate a ProcessService object from kubernetes object"""
        return self.get_process_ingress(app, kube_data)

    def get_rewrite_to_root(self, kube_data):
        target = kube_data.metadata.annotations.get(ANNOT_REWRITE_TARGET, "")
        return target == '/'

    def get_service_by_http_path(self, path) -> Tuple[str, str]:
        return path.backend.serviceName, path.backend.servicePort


# The correct value of "rewrite target" when ingress was configured to rewrite to "/"
REWRITE_TO_ROOT_REGEXP_TARGET = '/$2'


class ProcessIngressSerializerRegexpRewriteMixin:
    """Mixin class for handling regexp-based ingress rules"""

    def get_path_pattern(self, ingress: "ProcessIngress", path_str: str) -> str:
        """Get the path pattern, which will be written as ingress rules's path

        :param path_str: The raw inputted request path, without any regular expressions
        :return: regexp version of path_str, with extra "Capture groups"
        """
        if not ingress.rewrite_to_root:
            return path_str

        # Matches paths with no trailing slash and "/"
        if path_str == "/" or not path_str.endswith("/"):
            # Use an empty capture group to take the place of "$1", so the rewrite rule in
            # `get_rewrite_to_root_annots` can work as expected
            path_str = f"{path_str}()(.*)"
        else:
            # to adapter the path that ends without slash
            #
            # Handle both kinds of path： `/sub-path`(without trailing slash); '/sub-path/'(with trailing slash),
            # When using this pattern, make sure you have configured `rewrite-target` properly, see
            # `get_rewrite_to_root_annots` for more information
            # Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
            path_str = f"{path_str.rstrip('/')}(/|$)(.*)"

        return path_str

    def get_rewrite_to_root_annots(self, ingress: "ProcessIngress") -> Dict:
        # Below rewrite rule will discard the original `path_str` which was not captured by regexp
        # See `get_path_pattern` for more details
        #
        # Examples:
        # - path: /sub-path/, requested path: /sub-path/foobar
        # - $1: "/"
        # - $2: "foobar"
        #
        # - path: /sub-path/, requested path: /sub-path
        # - $1: ""
        # - $2: ""
        #
        return {ANNOT_REWRITE_TARGET: REWRITE_TO_ROOT_REGEXP_TARGET}


class ProcessIngressDeserializerRegexpRewriteMixin:
    re_rewrite_path_prefix = re.compile(r"^(?P<path>[\w\-/]*)(?P<pattern>.*?)$")

    def get_rewrite_to_root(self, kube_data) -> bool:
        path = kube_data.metadata.annotations.get(ANNOT_REWRITE_TARGET, "")
        # Also treat '/$1$2' as valid value for backward compatibility
        return path in {REWRITE_TO_ROOT_REGEXP_TARGET, '/$1$2'}

    def get_http_path(self, path: str) -> str:
        result = self.re_rewrite_path_prefix.search(path)
        if not result:
            return path

        groups = result.groupdict()
        real_path = groups["path"]
        pattern = groups["pattern"]

        if real_path.endswith("/") or not pattern:
            return real_path

        # 检测剩下的正则是否能匹配不以/开头的路径，以确定是否需要追加/
        match = re.match(pattern, "_")
        if match:
            return real_path
        return f"{real_path}/"


class ProcessIngressSerializerV1beta1(
    ProcessIngressSerializerRegexpRewriteMixin, ProcessIngressSerializerMixin, AppEntitySerializer['ProcessIngress']
):
    """Serializer for ProcessIngress

    IMPORTANT: `rewrite-target` uses regular expressions, not compatible with ingress-nginx < 0.22.0
    """

    # k8s 1.12-1.18
    api_version = 'networking.k8s.io/v1beta1'

    def get_http_path(self, ingress: "ProcessIngress", path_str: str) -> Dict:
        return {
            "path": self.get_path_pattern(ingress, path_str),
            "backend": {"serviceName": ingress.service_name, "servicePort": ingress.service_port_name},
        }

    def serialize(self, obj: AppEntity, original_obj=None, **kwargs) -> Dict:
        """Generate a kubernetes resource dict from ProcessIngress

        :param original_obj: if given, will update resource_version and other necessary fields
        """
        assert isinstance(obj, ProcessIngress), 'obj must be "ProcessIngress" type'
        resourceVersion = None
        if original_obj:
            resourceVersion = original_obj.metadata.resourceVersion

        return self.get_declaration(obj, resourceVersion)


class ProcessIngressDeserializerV1beta1(
    ProcessIngressDeserializerRegexpRewriteMixin,
    ProcessIngressDeserializerMixin,
    AppEntityDeserializer['ProcessIngress'],
):
    """IMPORTANT: `rewrite-target` uses regular expressions, not compatible with ingress-nginx < 0.22.0"""

    # k8s 1.12-1.18
    api_version = 'networking.k8s.io/v1beta1'

    def deserialize(self, app: App, kube_data) -> 'ProcessIngress':
        """Generate a ProcessService object from kubernetes object"""
        return self.get_process_ingress(app, kube_data)

    def get_service_by_http_path(self, path) -> Tuple[str, str]:
        return path.backend.serviceName, path.backend.servicePort


class ProcessIngressSerializerV1(
    ProcessIngressSerializerRegexpRewriteMixin, ProcessIngressSerializerMixin, AppEntitySerializer["ProcessIngress"]
):
    # k8s 1.19+
    api_version = "networking.k8s.io/v1"
    """IMPORTANT: `rewrite-target` uses regular expressions, not compatible with ingress-nginx < 0.22.0"""

    def get_http_path(self, ingress: "ProcessIngress", path_str: str) -> Dict:
        return {
            "path": self.get_path_pattern(ingress, path_str),
            "pathType": "ImplementationSpecific",
            "backend": {
                "service": {
                    "name": ingress.service_name,
                    "port": {"name": ingress.service_port_name},
                }
            },
        }

    def serialize(self, obj: AppEntity, original_obj=None, **kwargs) -> Dict:
        assert isinstance(obj, ProcessIngress), 'obj must be "ProcessIngress" type'
        resourceVersion = None
        if original_obj:
            resourceVersion = original_obj.metadata.resourceVersion

        return self.get_declaration(obj, resourceVersion)


class ProcessIngressDeserializerV1(
    ProcessIngressDeserializerRegexpRewriteMixin,
    ProcessIngressDeserializerMixin,
    AppEntityDeserializer["ProcessIngress"],
):
    """IMPORTANT: `rewrite-target` uses regular expressions, not compatible with ingress-nginx < 0.22.0"""

    # k8s 1.19+
    api_version = "networking.k8s.io/v1"

    def get_service_by_http_path(self, path) -> Tuple[str, str]:
        return path.backend.service.name, path.backend.service.port.name

    def deserialize(self, app: App, kube_data) -> 'ProcessIngress':
        return self.get_process_ingress(app, kube_data)


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


def get_domains_struct_type(domains: Sequence[PIngressDomain]) -> DomainsStructureType:
    """Calculate structure type of multiple domains"""
    prefixes = set()
    for domain in domains:
        prefixes.update(domain.path_prefix_list)

    if prefixes == {'/'}:
        return DomainsStructureType.ALL_DIRECT_ACCESS
    if '/' not in prefixes:
        # If non-default paths were configured for given domains, only consider it as "CUSTOMIZED_SUBPATH"
        # when domain's subpaths were identical with each other.
        #
        # Sort prefix list before calculating
        prefix_sets = [tuple(sorted(domain.path_prefix_list)) for domain in domains]
        if len(set(prefix_sets)) == 1:
            return DomainsStructureType.CUSTOMIZED_SUBPATH
    return DomainsStructureType.NON_STANDARD


def build_ingress_configs() -> Tuple[List, List]:
    """Build meta configs for `ProcessIngress` type, see `ENABLE_MODERN_INGRESS_SUPPORT`
    for more details.

    :return: (list of deserializers, list of serializers)
    """
    if settings.ENABLE_MODERN_INGRESS_SUPPORT:
        # MAY not compatible with ingress-nginx < 0.22.0 when `ProcessIngressDeserializerV1` or
        # `ProcessIngressDeserializerV1beta1` was picked.
        deserializers = [
            ProcessIngressDeserializerV1,
            ProcessIngressDeserializerV1beta1,
            ProcessIngressDeserializerExtV1beta1,
        ]
        serializers = [
            ProcessIngressSerializerV1,
            ProcessIngressSerializerV1beta1,
            ProcessIngressSerializerExtV1beta1,
        ]
    else:
        # Compatible with ingress-nginx < 0.22.0
        deserializers = [ProcessIngressDeserializerExtV1beta1]
        serializers = [ProcessIngressSerializerExtV1beta1]
    return deserializers, serializers


deserializers, serializers = build_ingress_configs()


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

    @property
    def domains_structure_type(self) -> DomainsStructureType:
        """Get current structure type of `self.domains`"""
        return get_domains_struct_type(self.domains)

    class Meta:
        kres_class = kres.KIngress
        deserializers = deserializers
        serializers = serializers


ingress_kmodel: AppEntityManager[ProcessIngress] = AppEntityManager[ProcessIngress](ProcessIngress)
