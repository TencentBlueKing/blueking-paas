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
"""high level scheduler functions related with app
"""
import logging
from typing import TYPE_CHECKING

from django.conf import settings

from paas_wl.deploy.app_res.client import K8sScheduler
from paas_wl.platform.applications.models.managers.app_res_ver import AppResVerManager
from paas_wl.resources.kube_res.base import Schedule
from paas_wl.resources.utils.basic import (
    get_client_by_app,
    get_cluster_by_app,
    get_full_node_selector,
    get_full_tolerations,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paas_wl.platform.applications.models import WlApp


def get_scheduler_client(cluster_name: str):
    """get scheduler by settings"""
    return K8sScheduler.from_cluster_name(cluster_name)


def get_scheduler_client_by_app(app: 'WlApp') -> 'K8sScheduler':
    """A wrapper function to make K8sSchedulerClient from a raw client object"""
    return K8sScheduler(
        get_client_by_app(app),
        settings.K8S_DEFAULT_CONNECT_TIMEOUT,
        settings.K8S_DEFAULT_READ_TIMEOUT,
        AppResVerManager(app).curr_version,
    )


def get_schedule_config(app: 'WlApp') -> 'Schedule':
    """Get the schedule config of an app."""
    return Schedule(
        cluster_name=get_cluster_by_app(app).name,
        node_selector=get_full_node_selector(app),
        tolerations=get_full_tolerations(app),
    )
