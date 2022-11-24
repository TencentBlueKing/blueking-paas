"""Address related functionalities"""
from typing import List

from attrs import define

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.platform.applications.models.app import EngineApp
from paas_wl.platform.applications.struct_models import ModuleEnv
from paas_wl.utils.basic import HumanizeURL

from .constants import AddressType, AppDomainSource
from .models import AppDomain, AppSubpath, Domain


@define
class Address:
    """Represents an exposed endpoint of application's deployed environments.

    :param type: Type of address
    :param url: URL, includes protocol and port number
    """

    type: AddressType
    url: str


class EnvAddresses:
    """Get addresses for deployed environment, includes data which come from
    different sources, such as builtin subdomain/subpath and custom domains.

    TODO: Add legacy engine URLS, see `ingress_config.default_ingress_domain_tmpl`
    for details.
    """

    def __init__(self, env: ModuleEnv):
        self.env = env
        self.app = env.application
        self.engine_app = EngineApp.objects.get_by_env(self.env)
        self.ingress_cfg = get_cluster_by_app(self.engine_app).ingress_config

    def get(self) -> List[Address]:
        """Get available addresses, sorted by: (subdomain, subpath, custom)"""
        from paas_wl.workloads.processes.controllers import env_is_running

        if not env_is_running(self.env):
            return []
        return self._get_subdomain() + self._get_subpath() + self._get_custom()

    def _get_subdomain(self) -> List[Address]:
        """Get addresses from subdomain source"""
        subdomains = AppDomain.objects.filter(app=self.engine_app, source=AppDomainSource.AUTO_GEN)
        return [Address(AddressType.SUBDOMAIN, self._make_url(d.https_enabled, d.host)) for d in subdomains]

    def _get_subpath(self) -> List[Address]:
        """Get addresses from subpath source"""
        path_objs = AppSubpath.objects.filter(app=self.engine_app).order_by('created')
        addrs = []
        for domain in self.ingress_cfg.sub_path_domains:
            for obj in path_objs:
                url = self._make_url(domain.https_enabled, domain.name, obj.subpath)
                addrs.append(Address(AddressType.SUBPATH, url))
        return addrs

    def _get_custom(self) -> List[Address]:
        """Get addresses from custom domains"""
        custom_domains = Domain.objects.filter(environment_id=self.env.id)
        # TODO: Add HTTPS support, currently hard code "http_enabled" to False
        return [Address(AddressType.CUSTOM, self._make_url(False, d.name, d.path_prefix)) for d in custom_domains]

    def _make_url(self, https_enabled: bool, host: str, path: str = '/') -> str:
        """Make URL address"""
        protocol = "https" if https_enabled else "http"
        port = self.ingress_cfg.port_map.get_port_num(protocol)
        return HumanizeURL(protocol, hostname=host, port=port, path=path).to_str()
