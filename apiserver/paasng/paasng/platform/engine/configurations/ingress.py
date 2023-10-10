"""Utilities related with ingress"""
from typing import Dict, List

from django.conf import settings

from paas_wl.networking.entrance.allocator.domains import Domain, ModuleEnvDomains
from paas_wl.networking.entrance.allocator.subpaths import ModuleEnvSubpaths, Subpath
from paas_wl.networking.ingress.shim import sync_subdomains, sync_subpaths
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType
from paasng.core.region.models import get_region


class AppDefaultDomains:
    """A helper class for dealing with app's default subdomains during building and releasing"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.engine_app = env.get_engine_app()

        self.domains: List[Domain] = []
        self.initialize_domains()

    def initialize_domains(self):
        """calculate and store app's default subdomains"""
        region = get_region(self.engine_app.region)
        # get domains only if current region was configured to use "SUBDOMAIN" type entrance
        if region.entrance_config.exposed_url_type == ExposedURLType.SUBDOMAIN:
            # calculate default subdomains
            self.domains = ModuleEnvDomains(self.env).all()

    def sync(self):
        """Sync app's default subdomains to engine"""
        sync_subdomains(self.env)

    def as_env_vars(self) -> Dict:
        """Return current subdomains as env vars"""
        domains_str = ';'.join(d.host for d in self.domains)

        if not domains_str:
            # only if domain exist, would add ENGINE_APP_DEFAULT_SUBDOMAINS key
            return {}

        return {settings.CONFIGVAR_SYSTEM_PREFIX + "ENGINE_APP_DEFAULT_SUBDOMAINS": domains_str}


class AppDefaultSubpaths:
    """A helper class for dealing with app's default subpaths during building and releasing"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.subpaths_service = ModuleEnvSubpaths(self.env)
        self.subpaths = self.subpaths_service.all()

    def sync(self):
        """Sync app's default subpaths to engine"""
        sync_subpaths(self.env)

    def as_env_vars(self) -> Dict:
        """Return current subpath as env vars"""
        obj = self.subpaths_service.get_shortest()
        if not obj:
            return {}

        return {
            settings.CONFIGVAR_SYSTEM_PREFIX + "SUB_PATH": self._build_sub_path_env(obj),
            settings.CONFIGVAR_SYSTEM_PREFIX + "DEFAULT_SUBPATH_ADDRESS": obj.as_url().as_address(),
        }

    def _build_sub_path_env(self, obj: Subpath):
        # TODO: remove FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE in settings
        if self.env.module.exposed_url_type is None or settings.FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE:
            # reserved for applications with legacy sub-path implementations
            engine_app = self.env.get_engine_app()
            return f"/{engine_app.region}-{engine_app.name}/"
        return obj.subpath
