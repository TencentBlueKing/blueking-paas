import os

import pytest
from django.core.management import call_command

from paas_wl.cluster.models import APIServer, Cluster

pytestmark = pytest.mark.django_db


@pytest.fixture()
def cluster_envs(monkeypatch):
    monkeypatch.setenv("PAAS_WL_CLUSTER_APP_ROOT_DOMAIN", "apps1.example.com")
    monkeypatch.setenv("PAAS_WL_CLUSTER_SUB_PATH_DOMAIN", "apps2.example.com")
    monkeypatch.setenv("PAAS_WL_CLUSTER_HTTP_PORT", "880")
    monkeypatch.setenv("PAAS_WL_CLUSTER_HTTPS_PORT", "8443")
    monkeypatch.setenv("PAAS_WL_CLUSTER_NODE_SELECTOR", "{\"dedicated\":\"bkSaas\"}")
    monkeypatch.setenv(
        "PAAS_WL_CLUSTER_TOLERATIONS",
        "[{\"effect\":\"NoSchedule\",\"key\":\"dedicated\",\"operator\":\"Equal\",\"value\":\"bkSaas\"}]",
    )
    monkeypatch.setenv(
        "PAAS_WL_CLUSTER_API_SERVER_URLS", "https://kubernetes.default.svc.cluster.localroot;https://10.0.0.1"
    )


@pytest.mark.parametrize(
    "https_enabled, expect",
    [
        ("true", True),
        ("false", False),
    ],
)
def test_init_cluster(cluster_envs, https_enabled, expect):
    os.environ["PAAS_WL_CLUSTER_ENABLED_HTTPS_BY_DEFAULT"] = https_enabled

    call_command("initial_default_cluster")

    cluster = Cluster.objects.get(name="default-main")

    ingress_config = cluster.ingress_config
    assert ingress_config.app_root_domains[0].https_enabled is expect
    assert ingress_config.sub_path_domains[0].https_enabled is expect
    assert ingress_config.app_root_domains[0].name == "apps1.example.com"
    assert ingress_config.sub_path_domains[0].name == "apps2.example.com"
    assert ingress_config.port_map.http == 880
    assert ingress_config.port_map.https == 8443
    assert cluster.default_tolerations == [
        {'effect': 'NoSchedule', 'key': 'dedicated', 'operator': 'Equal', 'value': 'bkSaas'}
    ]
    assert cluster.default_node_selector == {"dedicated": "bkSaas"}
    urls = APIServer.objects.filter(cluster=cluster).values_list("host", flat=True)
    assert set(urls) == set(['https://kubernetes.default.svc.cluster.localroot', "https://10.0.0.1"])
