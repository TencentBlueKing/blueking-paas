# -*- coding: utf-8 -*-
from paas_wl.cluster.models import Cluster
from paas_wl.platform.applications.models.app import App


def get_default_cluster_by_region(region: str) -> Cluster:
    """Get default cluster name by region"""
    try:
        return Cluster.objects.get(is_default=True, region=region)
    except Cluster.DoesNotExist:
        raise RuntimeError(f'No default cluster found in region `{region}`')


def get_cluster_by_app(app: App) -> Cluster:
    """Get kubernetes cluster by given app

    :raise RuntimeError: App has an invalid cluster_name defined
    """
    cluster_name = app.config_set.latest().cluster

    if not cluster_name:
        cluster = get_default_cluster_by_region(app.region)
    else:
        try:
            cluster = Cluster.objects.get(name=cluster_name)
        except Cluster.DoesNotExist:
            raise RuntimeError(f'Can not find a cluster called {cluster_name}')
    return cluster
