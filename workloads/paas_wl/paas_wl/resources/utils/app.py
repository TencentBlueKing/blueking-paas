# -*- coding: utf-8 -*-
"""high level scheduler functions related with app
"""
import logging
from typing import TYPE_CHECKING

from django.conf import settings

from paas_wl.platform.applications.models.managers.app_res_ver import AppResVerManager
from paas_wl.resources.base.client import K8sScheduler
from paas_wl.resources.utils.basic import get_client_by_app

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paas_wl.platform.applications.models.app import App


def get_scheduler_client(cluster_name: str):
    """get scheduler by settings"""
    return K8sScheduler.from_cluster_name(cluster_name)


def get_scheduler_client_by_app(app: 'App') -> 'K8sScheduler':
    """A wrapper function to make K8sSchedulerClient from a raw client object"""
    return K8sScheduler(
        get_client_by_app(app),
        settings.K8S_DEFAULT_CONNECT_TIMEOUT,
        settings.K8S_DEFAULT_READ_TIMEOUT,
        AppResVerManager(app).curr_version,
    )
