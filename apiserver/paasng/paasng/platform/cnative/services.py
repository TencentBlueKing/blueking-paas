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
from typing import Dict, List, Optional

from django.utils.translation import gettext_lazy as _

from paas_wl.bk_app.applications.api import (
    create_app_ignore_duplicated,
    create_cnative_app_model_resource,
    update_metadata_by_env,
)
from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.cnative.specs.constants import ApiVersion
from paas_wl.infras.cluster.shim import EnvClusterService, RegionClusterService
from paasng.accessories.log.shim import setup_env_log_model
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.manager import ModuleInitializer, make_engine_app_name
from paasng.platform.modules.models import Module
from paasng.utils.configs import get_region_aware
from paasng.utils.error_codes import error_codes

# Model-Resource
default_environments: List[str] = [AppEnvName.STAG.value, AppEnvName.PROD.value]


def initialize_simple(
    module: Module,
    image: str,
    cluster_name: Optional[str] = None,
    api_version: Optional[str] = ApiVersion.V1ALPHA2,
    command: Optional[List[str]] = None,
    args: Optional[List[str]] = None,
    target_port: Optional[int] = None,
) -> Dict:
    """Initialize a cloud-native application, return the initialized object

    :param module: Module object, a module can only be initialized once
    :param image: The container image of main process
    :param cluster_name: The name of cluster to deploy BkApp.
    :param command: Custom command
    :param args: Custom args
    :param target_port: Custom target port
    """
    if not cluster_name:
        cluster_name = get_default_cluster_name(module.region)

    model_res = create_cnative_app_model_resource(module, image, api_version, command, args, target_port)
    create_engine_apps(module.application, module, environments=default_environments, cluster_name=cluster_name)
    return model_res


def create_engine_apps(
    application: Application,
    module: Module,
    cluster_name: str,
    environments: Optional[List[str]] = None,
):
    """Create engine app instances for application"""
    environments = environments or default_environments
    for environment in environments:
        engine_app_name = make_engine_app_name(module, application.code, environment)
        # 先创建 EngineApp，再更新相关的配置（比如 cluster_name）
        engine_app = get_or_create_engine_app(application.owner, application.region, engine_app_name)
        env = ModuleEnvironment.objects.create(
            application=application, module=module, engine_app_id=engine_app.id, environment=environment
        )
        EnvClusterService(env).bind_cluster(cluster_name)
        setup_env_log_model(env)

        # Update metadata
        engine_app_meta_info = ModuleInitializer(module).make_engine_meta_info(env)
        update_metadata_by_env(env, engine_app_meta_info)


def get_or_create_engine_app(owner: str, region: str, engine_app_name: str) -> EngineApp:
    """get or create engine app from workload

    :return: EngineApp object
    """
    info = create_app_ignore_duplicated(region, engine_app_name, WlAppType.CLOUD_NATIVE)
    # Create EngineApp and binding relationships
    return EngineApp.objects.create(
        id=info.uuid,
        name=engine_app_name,
        owner=owner,
        region=region,
    )


def get_default_cluster_name(region: str) -> str:
    """Get default cluster name from settings, and valid if we have this cluster."""
    try:
        default_cluster_name = get_region_aware("CLOUD_NATIVE_APP_DEFAULT_CLUSTER", region)
    except Exception as e:
        raise error_codes.CANNOT_CREATE_APP.f(_("暂无可用集群, 请联系管理员")) from e

    try:
        return RegionClusterService(region).get_cluster_by_name(default_cluster_name).name
    except Exception:
        raise error_codes.CANNOT_CREATE_APP.f(_(f"集群 {default_cluster_name} 未就绪, 请联系管理员"))
