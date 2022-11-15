# -*- coding: utf-8 -*-
import contextlib
import logging
from typing import Any, Dict, List, Optional
from urllib import parse

from attrs import Factory, asdict, define
from cattr import register_structure_hook, structure_attrs_fromdict
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.db import models, transaction
from jsonfield import JSONField
from kubernetes.client import Configuration

from paas_wl.cluster.constants import ClusterTokenType
from paas_wl.cluster.exceptions import DuplicatedDefaultClusterError, NoDefaultClusterError, SwitchDefaultClusterError
from paas_wl.cluster.validators import validate_ingress_config
from paas_wl.utils.dns import custom_resolver
from paas_wl.utils.models import UuidAuditedModel, make_json_field

logger = logging.getLogger(__name__)


@define
class PortMap:
    """PortMap is used to declare the port of http/https protocol exposed by the ingress gateway."""

    http: int = 80
    https: int = 443

    def get_port_num(self, protocol: str) -> int:
        """Return port number by protocol"""
        return asdict(self)[protocol]


@define
class Domain:
    name: str
    # reserved: 表示该域名是否保留域名
    reserved: bool = False
    # https_enabled: 表示该域名是否打开 HTTPS 访问（要求提供对应证书）
    https_enabled: bool = False

    @staticmethod
    def structure(obj, cl):
        """对旧数据结构的兼容逻辑"""
        if isinstance(obj, str):
            return cl(name=obj)
        return structure_attrs_fromdict(obj, cl)


register_structure_hook(Domain, Domain.structure)


@define
class IngressConfig:
    # [保留选项] 一个默认的 Ingress 域名字符串模板，形如 "%s.example.com"。当该选项有值时，
    # 系统会为每个应用创建一个匹配域名 "{app_scheduler_name}.example.com" 的独一无二的 Ingress
    # 资源。配合其他负载均衡器，可完成复杂的请求转发逻辑。
    #
    # 该配置仅供特殊环境中使用，大部分情况下，请直接使用 app_roo_domains 和 sub_path_domains。
    default_ingress_domain_tmpl: str = ''

    # 支持的子域名的根域列表, 在需要获取单个值的地方, 会优先使用第一个配置的根域名.
    app_root_domains: List[Domain] = Factory(list)
    # 支持的子路径的根域列表, 在需要获取单个值的地方, 会优先使用第一个配置的根域名.
    sub_path_domains: List[Domain] = Factory(list)
    # Ip address of frontend ingress controller
    frontend_ingress_ip: str = ''
    port_map: PortMap = Factory(PortMap)


class ClusterManager(models.Manager):
    @transaction.atomic()
    def register_cluster(
        self,
        region: str,
        name: str,
        is_default: bool = False,
        description: Optional[str] = None,
        ingress_config: Optional[Dict] = None,
        annotations: Optional[Dict] = None,
        ca_data: Optional[str] = None,
        cert_data: Optional[str] = None,
        key_data: Optional[str] = None,
        token_type: Optional[ClusterTokenType] = None,
        token_value: Optional[str] = None,
        default_node_selector: Optional[Dict] = None,
        default_tolerations: Optional[List] = None,
        pk: Optional[str] = None,
        **kwargs,
    ) -> 'Cluster':
        """Register a cluster to db, work Like update_or_create, but will validate some-attr

        Auth type: client-side cert
        ---------------------------

        :param cert_data: client cert data
        :param key_data: client key data

        Auth type: Bearer token
        -----------------------

        :param token_type: token type, use `SERVICE_ACCOUNT` by default
        :param token_value: value of token
        """
        default_cluster_qs = self.filter(region=region, is_default=True)

        if not default_cluster_qs.exists() and not is_default:
            raise NoDefaultClusterError("This region has not define a default cluster.")
        elif default_cluster_qs.filter(name=name).exists() and not is_default:
            raise SwitchDefaultClusterError(
                "Can't change default cluster by calling `register_cluster`, please use `switch_default_cluster`"
            )
        elif default_cluster_qs.exclude(name=name).exists() and is_default:
            raise DuplicatedDefaultClusterError("This region should have one and only one default cluster.")

        validate_ingress_config(ingress_config)

        defaults: Dict[str, Any] = {
            "is_default": is_default,
            "description": description,
            "ingress_config": ingress_config,
            "annotations": annotations,
            "ca_data": ca_data,
            "cert_data": cert_data,
            "key_data": key_data,
            "default_node_selector": default_node_selector,
            "default_tolerations": default_tolerations,
        }
        if token_value:
            _token_type = token_type or ClusterTokenType.SERVICE_ACCOUNT
            defaults.update({'token_value': token_value, 'token_type': _token_type})

        # We use `None` to mark this fields is unset, so we should pop it from defaults.
        defaults = {k: v for k, v in defaults.items() if v is not None}

        if pk:
            cluster, _ = self.update_or_create(pk=pk, name=name, region=region, defaults=defaults)
        else:
            cluster, _ = self.update_or_create(name=name, region=region, defaults=defaults)
        return cluster

    @transaction.atomic
    def switch_default_cluster(self, region: str, cluster_name: str) -> 'Cluster':
        """Switch the default cluster to the cluster called `cluster_name`.

        :raise SwitchDefaultClusterException: if the cluster called `cluster_name` is already the default cluster.
        """
        try:
            prep_default_cluster = self.get(region=region, name=cluster_name)
            curr_default_cluster = self.get(region=region, is_default=True)
        except self.model.DoesNotExist:
            raise SwitchDefaultClusterError("Can't switch default cluster to a not-existed cluster.")

        if prep_default_cluster.name == curr_default_cluster.name:
            raise SwitchDefaultClusterError("The cluster is already the default cluster.")

        curr_default_cluster.is_default = False
        prep_default_cluster.is_default = True

        curr_default_cluster.save()
        prep_default_cluster.save()

        return prep_default_cluster


IngressConfigField = make_json_field(cls_name="IngressConfigField", py_model=IngressConfig)


class Cluster(UuidAuditedModel):
    def __str__(self):
        return f"{self.__class__.__name__}(name={self.name}, default={self.is_default})"

    region = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=32, help_text="name of the cluster", unique=True)
    description = models.TextField(help_text="描述信息", blank=True)
    is_default = models.NullBooleanField(default=False)

    ingress_config: IngressConfig = IngressConfigField()
    annotations = JSONField(default={}, help_text="Annotations are used to add metadata to describe the cluster.")

    ca_data = models.TextField(null=True)
    # Auth type 1. Client-side certificate
    cert_data = models.TextField(null=True)
    key_data = models.TextField(null=True)
    # Auth type 2. Bearer token
    token_type = models.IntegerField(null=True)
    token_value = models.TextField(null=True)

    # App related default configs
    default_node_selector = JSONField(default={}, help_text="default value for app's 'node_selector' field")
    default_tolerations = JSONField(default=[], help_text="default value for app's 'tolerations' field")

    objects = ClusterManager()

    @property
    def bcs_cluster_id(self) -> Optional[str]:
        """Property 'bcs_cluster_id' of cluster object, return None when not configured"""
        return self.annotations.get('bcs_cluster_id', None)


class APIServer(UuidAuditedModel):
    cluster = models.ForeignKey(to=Cluster, related_name="api_servers", on_delete=models.CASCADE)
    host = models.CharField(max_length=255, help_text="API Server 的后端地址")
    overridden_hostname = models.CharField(
        max_length=255,
        help_text="在请求该 APIServer 时, 使用该 hostname 替换具体的 backend 中的 hostname",
        default=None,
        blank=True,
        null=True,
    )

    class Meta:
        unique_together = ("cluster", "host")


class EnhancedConfiguration(Configuration):
    """Enhanced Configuration, which is loaded from db and supporting advanced function.

    :param cert_file: client-side certificate file
    :param key_file: client-side key file
    :parma token: bearer token
    """

    @classmethod
    def create(
        cls, host: str, overridden_hostname: str, ssl_ca_cert: str, cert_file: str, key_file: str, token: Optional[str]
    ):
        """Create an `EnhancedConfiguration` object.

        由于 Swagger 在重载 __init__ 方法时不允许添加参数, 因此定义另一个工厂函数

        :param overridden_hostname: Replace host with this value. A custom resolver is required to make
            sure the request is sending to the right host. For example: when host="https://192.168.1.1:8443/"
            and overridden_hostname="kubernetes". The request will be send to "https://kubernetes:8443/"
            while domain "kubernetes" resolved to "192.168.1.1".
        :raise ValueError: When given properties is not valid.
        """
        self = cls()
        # Set properties afterwards
        self._initialize_host(host, overridden_hostname)
        self._initialize_auth(ssl_ca_cert, cert_file, key_file, token)
        return self

    def _initialize_host(self, host: str, forced_hostname: str):
        """Initialize host and DNS resolver related properties"""
        if forced_hostname:
            ip = self.extract_ip(host)
            if not ip:
                raise ValueError(f'No IP address found in {host}')
            self.host = host.replace(ip, forced_hostname, 1)
            self.resolver_records = {forced_hostname: ip}
        else:
            self.host = host
            self.resolver_records = {}

    def _initialize_auth(self, ssl_ca_cert: str, cert_file: str, key_file: str, token: Optional[str]):
        """Initialize auth related properties"""
        if ssl_ca_cert:
            self.ssl_ca_cert = ssl_ca_cert
        else:
            self.verify_ssl = False

        # Auth type: client-side certificate
        if cert_file and key_file:
            self.cert_file = cert_file
            self.key_file = key_file

        # Auth type: Bearer token
        if token:
            token = f'Bearer {token}'
            self.api_key['authorization'] = token

    @contextlib.contextmanager
    def activate_resolver(self):
        """Activate this context manager when sending any API requests to make "hostname-override" works"""
        if self.resolver_records:
            logger.debug('Custom resolver record: %s', self.resolver_records)
            with custom_resolver(self.resolver_records):
                yield
        else:
            yield

    @staticmethod
    def extract_ip(host: str) -> Optional[str]:
        """Extract an IP address from host

        :return: None if the host is not valid IP address
        """
        val = parse.urlparse(url=host).hostname
        try:
            validate_ipv46_address(val)
        except ValidationError:
            return None
        return val

    def __repr__(self) -> str:
        return f'EnhancedConfiguration(host={self.host!r})'
