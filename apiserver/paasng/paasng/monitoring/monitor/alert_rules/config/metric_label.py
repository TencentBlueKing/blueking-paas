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

from paasng.dev_resources.servicehub.constants import Category
from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


def get_vhost(app_code: str, run_env: str, module_name: str) -> Optional[str]:
    app = Application.objects.get(code=app_code)
    app_module = app.get_module(module_name)

    for bound_service in mixed_service_mgr.list_binded(app_module, category_id=Category.DATA_STORAGE):
        if bound_service.name == 'rabbitmq':
            svc_obj = mixed_service_mgr.get(bound_service.uuid, app.region)
            break
    else:
        logger.info(f'RabbitMQ service not found or not bounded with app: {app_code}, module: {module_name}')
        return None

    for rel in mixed_service_mgr.list_provisioned_rels(app_module.get_envs(run_env).engine_app, svc_obj):
        # 只取第一个 vhost
        return rel.get_instance().credentials['RABBITMQ_VHOST']

    return None


def get_namespace(app_code: str, run_env: str, module_name: str) -> Optional[str]:
    try:
        return _get_namespace_cache(app_code, run_env, module_name)
    except Exception:
        return None


@functools.lru_cache(maxsize=10)
def _get_namespace_cache(app_code: str, run_env: str, module_name: str) -> str:
    return Application.objects.get(code=app_code).get_engine_app(run_env, module_name).name


LABEL_VALUE_QUERY_FUNCS: Dict[str, Callable[..., Optional[str]]] = {
    'namespace': get_namespace,
    'vhost': get_vhost,
}


def get_metric_labels(metric_names: List[str], app_code: str, run_env: str, module_name: str) -> Dict[str, str]:
    """Get metric labels based on the provided metric names"""
    labels: Dict[str, str] = {}
    for name in metric_names:
        if (value := LABEL_VALUE_QUERY_FUNCS[name](app_code, run_env, module_name)) is not None:
            labels[name] = value
    return labels
