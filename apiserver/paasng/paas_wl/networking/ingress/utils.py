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
import logging

from paas_wl.networking.ingress.entities.ingress import ingress_kmodel
from paas_wl.platform.applications.constants import WlAppType
from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound

logger = logging.getLogger(__name__)


def make_service_name(app: WlApp, process_type: str) -> str:
    """Return the service name for each process"""
    if app.type == WlAppType.CLOUD_NATIVE:
        return process_type
    return f"{app.region}-{app.scheduler_safe_name}-{process_type}"


def parse_process_type(app: WlApp, service_name: str) -> str:
    """Parse process type from service name

    :param app: WlApp object
    :param service_name: Name of Service resource.
    :raise ValueError: When given service_name is not parsable.
    """
    if app.type == WlAppType.CLOUD_NATIVE:
        return service_name
    parts = service_name.split(app.scheduler_safe_name)
    if len(parts) == 1:
        raise ValueError(f'Service name "{service_name}" invalid')
    # Remove leading "-" char, ["bkapp-", "-web"] -> "web"
    return parts[-1][1:]


def get_service_dns_name(app: WlApp, process_type: str) -> str:
    """Return process's DNS name, can be used for communications across processes.

    :param app: WlApp object
    :param process_type: Process Type, e.g. "web"
    """
    return f'{make_service_name(app, process_type)}.{app.namespace}'


def guess_default_service_name(app: WlApp) -> str:
    """Guess the default service name should be used when a brand new ingress creation is required."""
    if not app.get_structure():
        return make_service_name(app, 'web')
    if 'web' in app.get_structure():
        return make_service_name(app, 'web')
    # Pick a random process type for generating service name
    return make_service_name(app, list(app.get_structure().keys())[0])


def get_main_process_service_name(app: WlApp) -> str:
    """
    获取提供服务的主进程 Service Name

    直接从 K8S 数据查询
    """
    # 理论上，任何一个 ingress 指向的 service 都应该是当前主进程绑定的 Service
    ingresses = ingress_kmodel.list_by_app(app)
    if not ingresses:
        raise AppEntityNotFound("no ingress found")

    return ingresses[0].service_name
