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
import functools
import logging
from typing import Callable, Dict, List, Optional

from kubernetes.client.apis import VersionApi

from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.misc.monitoring.monitor.exceptions import BKMonitorNotSupportedError
from paasng.platform.applications.models import Application, ApplicationEnvironment
from paasng.platform.modules.constants import ModuleName

from .constants import RABBITMQ_SERVICE_NAME

logger = logging.getLogger(__name__)


def get_vhost(app_code: str, run_env: str, module_name: Optional[str] = None) -> str:
    if not module_name:
        raise ValueError(f'get_vhost(app_code: {app_code}): module_name is required')

    app = Application.objects.get(code=app_code)

    try:
        svc_obj = mixed_service_mgr.find_by_name(name=RABBITMQ_SERVICE_NAME, region=app.region)
    except ServiceObjNotFound as e:
        logger.info(e)
        return ''

    app_module = app.get_module(module_name)
    if env_vars := mixed_service_mgr.get_env_vars(app_module.get_envs(run_env).engine_app, svc_obj):
        return env_vars['RABBITMQ_VHOST']

    logger.info(f'RabbitMQ service not bounded with app: {app_code}, module: {module_name}')
    return ''


def get_namespace(app_code: str, run_env: str, module_name: Optional[str] = None) -> str:
    # 如果不传递模块, 则使用 default 模块(云原生应用各个模块和 default 模块部署在相同的命名空间下)
    module_name = module_name or ModuleName.DEFAULT.value
    return _get_namespace_cache(app_code, run_env, module_name)


def get_cluster_id(app_code: str, run_env: str, module_name: Optional[str] = None) -> str:
    """
    获取集群 ID

    :param app_code: 应用 code
    :param run_env: 环境
    :param module_name: 模块名
    :raises NotImplementedError: 集群版本低于 1.12
    """
    # 如果不传递模块, 则使用 default 模块(云原生应用各个模块和 default 模块部署在相同的命名空间下)
    module_name = module_name or ModuleName.DEFAULT.value
    cluster_info = _get_cluster_info_cache(app_code, run_env, module_name)
    version = cluster_info['version']
    if (int(version.major), int(version.minor.rstrip('+'))) < (1, 12):
        raise BKMonitorNotSupportedError(f'bkmonitor does not support k8s version {version} which below 1.12')

    return cluster_info['bcs_cluster_id']


@functools.lru_cache(maxsize=32)
def _get_namespace_cache(app_code: str, run_env: str, module_name: str) -> str:
    return ApplicationEnvironment.objects.get(
        application__code=app_code, module__name=module_name, environment=run_env
    ).wl_app.namespace


@functools.lru_cache(maxsize=32)
def _get_cluster_info_cache(app_code: str, run_env: str, module_name: str) -> dict:
    wl_app = ApplicationEnvironment.objects.get(
        application__code=app_code, module__name=module_name, environment=run_env
    ).wl_app
    cluster = get_cluster_by_app(wl_app)
    client = get_client_by_cluster_name(cluster.name)
    version = VersionApi(client).get_code()
    return {
        'bcs_cluster_id': cluster.bcs_cluster_id,
        'version': version,
    }


LABEL_VALUE_QUERY_FUNCS: Dict[str, Callable[[str, str, Optional[str]], str]] = {
    'namespace': get_namespace,
    'vhost': get_vhost,
    'bcs_cluster_id': get_cluster_id,
}


def get_metric_labels(
    metric_names: List[str], app_code: str, run_env: str, module_name: Optional[str] = None
) -> Dict[str, str]:
    """Get metric labels based on the provided metric names"""
    labels: Dict[str, str] = {}
    for name in metric_names:
        if value := LABEL_VALUE_QUERY_FUNCS[name](app_code, run_env, module_name):
            labels[name] = value
    return labels
