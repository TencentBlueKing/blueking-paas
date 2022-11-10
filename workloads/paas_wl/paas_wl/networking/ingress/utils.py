# -*- coding: utf-8 -*-
import logging

from paas_wl.networking.ingress.entities.ingress import ingress_kmodel
from paas_wl.platform.applications.models import EngineApp
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound

logger = logging.getLogger(__name__)


def make_service_name(app: EngineApp, process_type: str) -> str:
    """Return the service name for each process"""
    return f"{app.region}-{app.scheduler_safe_name}-{process_type}"


def get_service_dns_name(app: EngineApp, process_type: str) -> str:
    """Return process's DNS name, can be used for communications across processes.

    :param app: EngineApp object
    :param process_type: Process Type, e.g. "web"
    """
    return f'{make_service_name(app, process_type)}.{app.namespace}'


def guess_default_service_name(app: EngineApp) -> str:
    """Guess the default service name should be used when a brand new ingress creation is required."""
    if not app.get_structure():
        return make_service_name(app, 'web')
    if 'web' in app.get_structure():
        return make_service_name(app, 'web')
    # Pick a random process type for generating service name
    return make_service_name(app, list(app.get_structure().keys())[0])


def get_main_process_service_name(app: EngineApp) -> str:
    """
    获取提供服务的主进程 Service Name

    直接从 K8S 数据查询
    """
    # 理论上，任何一个 ingress 指向的 service 都应该是当前主进程绑定的 Service
    ingresses = ingress_kmodel.list_by_app(app)
    if not ingresses:
        raise AppEntityNotFound("no ingress found")

    return ingresses[0].service_name
