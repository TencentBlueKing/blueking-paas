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
"""Provide functions for the apiserver module.

- Functions should be as few as possible
- Do not return the models in workloads directly when a simple data class is sufficient

Other modules which have similar purpose:

- paasng.engine.deploy.engine_svc.EngineDeployClient
- paasng.engine.models.processes.ProcessManager

These modules will be refactored in the future.
"""
from typing import Dict, List, NamedTuple, Optional, Union
from uuid import UUID

from django.db import transaction

from paas_wl.platform.applications.constants import WlAppType
from paas_wl.platform.applications.models import WlApp
from paas_wl.platform.applications.models.managers.app_metadata import WlAppMetadata, get_metadata, update_metadata
from paas_wl.workloads.processes.models import ProcessSpec
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module


class CreatedAppInfo(NamedTuple):
    uuid: UUID
    name: str


def create_app_ignore_duplicated(region: str, name: str, type_: WlAppType) -> CreatedAppInfo:
    """Create an engine app object, return directly if the object already exists"""
    try:
        obj = WlApp.objects.get(region=region, name=name)
    except WlApp.DoesNotExist:
        obj = WlApp.objects.create(region=region, name=name, type=type_)
    return CreatedAppInfo(obj.uuid, obj.name)


def get_metadata_by_env(env: ModuleEnvironment) -> WlAppMetadata:
    """Get an environment's metadata"""
    wl_app = WlApp.objects.get(pk=env.engine_app_id)
    return get_metadata(wl_app)


def update_metadata_by_env(env: ModuleEnvironment, metadata_part: Dict[str, Union[str, bool]]):
    """Update an environment's metadata, works like python's dict.update()

    :param metadata_part: An dict object which will be merged into app's metadata
    """
    wl_app = WlApp.objects.get(pk=env.engine_app_id)
    update_metadata(wl_app, **metadata_part)


def delete_wl_resources(env: ModuleEnvironment):
    """Delete all resources of the given environment in workloads module, this function
    should be called when user deletes an application/module/env.

    :param env: Environment object.
    """
    from paas_wl.resources.actions.delete import delete_env_resources

    delete_env_resources(env)

    wl_app = env.wl_app
    # Delete some related records manually. Because during API migration, those related data
    # was stored in another database and the `Foreignkey` mechanism can't handle this situation.
    # TODO: Remove below lines when data was fully migrated
    ProcessSpec.objects.filter(engine_app_id=wl_app.pk).delete()
    wl_app.delete()


def delete_module_related_res(module: 'Module'):
    """Delete module's related resources"""
    from paas_wl.platform.applications.models_utils import delete_module_related_res as delete_wl_module_related_res

    with transaction.atomic(using="default"), transaction.atomic(using="workloads"):
        delete_wl_module_related_res(module)
        # Delete related EngineApp db records
        for env in module.get_envs():
            env.get_engine_app().delete()


def create_cnative_app_model_resource(
    module: Module,
    image: str,
    command: Optional[List[str]] = None,
    args: Optional[List[str]] = None,
    target_port: Optional[int] = None,
) -> Dict:
    """Create a cloud-native AppModelResource object

    :param module: The Module object current app model resource bound with
    """
    from paas_wl.cnative.specs.models import AppModelResource, create_app_resource

    application = module.application
    resource = create_app_resource(
        # Use Application code as default resource name
        name=application.code,
        image=image,
        command=command,
        args=args,
        target_port=target_port,
    )
    model_resource = AppModelResource.objects.create_from_resource(
        application.region, str(application.id), str(module.id), resource
    )
    return {
        'application_id': model_resource.application_id,
        'module_id': model_resource.module_id,
        'manifest': model_resource.revision.json_value,
    }


def upsert_app_monitor(
    engine_app_name: str,
    port: int,
    target_port: int,
):
    from paas_wl.monitoring.app_monitor.models import AppMetricsMonitor

    instance, _ = AppMetricsMonitor.objects.update_or_create(
        defaults={
            "port": port,
            "target_port": target_port,
            "is_enabled": True,
        },
        app=WlApp.objects.get(name=engine_app_name),
    )
