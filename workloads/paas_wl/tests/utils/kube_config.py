# -*- coding: utf-8 -*-
import base64

from django.conf import settings

from paas_wl.cluster.loaders import LegacyKubeConfigLoader
from paas_wl.cluster.models import APIServer, Cluster


def _load_file(filename):
    with open(filename, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def init_kube_config_from_yaml(file: str = '', clear: bool = False):
    """
    :param file: path to kube config file
    :param clear: Whether to clean up kube config info in DB
    """
    if clear:
        Cluster.objects.all().delete()

    loader = LegacyKubeConfigLoader.from_file(file or settings.KUBE_CONFIG_FILE)
    for tag in loader.get_all_tags():
        for config in loader.list_configurations_by_tag(tag):
            cluster = Cluster.objects.register_cluster(
                name=tag,
                region=settings.FOR_TESTS_DEFAULT_REGION,
                is_default=not Cluster.objects.filter(region=settings.FOR_TESTS_DEFAULT_REGION).exists(),
                ca_data=_load_file(config.ssl_ca_cert),
                cert_data=_load_file(config.cert_file),
                key_data=_load_file(config.key_file),
                ingress_config={
                    "app_root_domains": [{"name": "example.com"}],
                    "default_ingress_domain_tmpl": "%s.apps.com",
                    "frontend_ingress_ip": "0.0.0.0",
                    "port_map": {"http": "80", "https": "443"},
                },
            )
            api_server, _ = APIServer.objects.get_or_create(
                host=config.host,
                cluster=cluster,
                defaults=dict(
                    overridden_hostname=config.overridden_hostname,
                ),
            )
