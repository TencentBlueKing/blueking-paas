# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from typing import Dict, List

from paas_wl.bk_app.applications.api import (
    create_app_ignore_duplicated,
    create_cnative_app_model_resource,
    update_metadata_by_env,
)
from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.cnative.specs.constants import ApiVersion
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator, EnvClusterService
from paasng.accessories.log.shim import setup_env_log_model
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.manager import ModuleInitializer, make_engine_app_name
from paasng.platform.modules.models import Module

# Model-Resource
default_environments: List[str] = [AppEnvName.STAG.value, AppEnvName.PROD.value]


def initialize_simple(
    module: Module,
    image: str,
    cluster_name: str | None = None,
    api_version: str | None = ApiVersion.V1ALPHA2,
    command: List[str] | None = None,
    args: List[str] | None = None,
    target_port: int | None = None,
) -> Dict:
    """Initialize a cloud-native application, return the initialized object
    注意：该方法仅提供给单元测试使用 TODO (su) 从该模块中移出

    :param module: Module object, a module can only be initialized once
    :param image: The container image of main process
    :param cluster_name: The name of cluster to deploy BkApp.
    :param command: Custom command
    :param args: Custom args
    :param target_port: Custom target port
    """
    model_res = create_cnative_app_model_resource(module, image, api_version, command, args, target_port)
    create_engine_apps(module.application, module, environments=default_environments, cluster_name=cluster_name)
    return model_res


def create_engine_apps(
    application: Application,
    module: Module,
    cluster_name: str | None,
    environments: List[str] | None = None,
):
    """Create engine app instances for application"""
    environments = environments or default_environments
    for environment in environments:
        engine_app_name = make_engine_app_name(module, application.code, environment)
        # 先创建 EngineApp，再更新相关的配置（比如 cluster_name）
        engine_app = get_or_create_engine_app(
            application.owner, application.region, engine_app_name, application.tenant_id
        )
        env = ModuleEnvironment.objects.create(
            application=application,
            module=module,
            engine_app_id=engine_app.id,
            environment=environment,
            tenant_id=application.tenant_id,
        )
        if not cluster_name:
            ctx = AllocationContext.from_module_env(env)
            cluster_name = ClusterAllocator(ctx).get_default().name

        EnvClusterService(env).bind_cluster(cluster_name)
        setup_env_log_model(env)

        # Update metadata
        engine_app_meta_info = ModuleInitializer(module).make_engine_meta_info(env)
        update_metadata_by_env(env, engine_app_meta_info)


def get_or_create_engine_app(owner: str, region: str, engine_app_name: str, tenant_id: str) -> EngineApp:
    """get or create engine app from workload

    :return: EngineApp object
    """
    info = create_app_ignore_duplicated(region, engine_app_name, WlAppType.CLOUD_NATIVE, tenant_id)
    # Create EngineApp and binding relationships
    return EngineApp.objects.create(
        id=info.uuid, name=engine_app_name, owner=owner, region=region, tenant_id=tenant_id
    )


def check_replicas_manually_scaled(m: Module) -> bool:
    """check if replicas has been manually scaled by web form"""
    process_names = ModuleProcessSpec.objects.filter(module=m).values_list("name", flat=True)

    if not process_names:
        return False

    # NOTE: 页面手动扩缩容会修改 spec.env_overlay.replicas 的管理者为 web_form, 因此只需要检查 f_overlay_replicas 字段
    replicas_fields = []
    for proc_name in process_names:
        for env_name in AppEnvName:
            replicas_fields.append(fieldmgr.f_overlay_replicas(proc_name, env_name))

    managers = fieldmgr.MultiFieldsManager(m).get(replicas_fields)
    return fieldmgr.FieldMgrName.WEB_FORM in managers.values()
