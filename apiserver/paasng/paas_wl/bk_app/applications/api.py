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

"""Provide functions for the apiserver module.

- Functions should be as few as possible
- Do not return the models in workloads directly when a simple data class is sufficient

Other modules which have similar purpose:

- paasng.platform.engine.deploy.utils.client.EngineDeployClient
- paasng.platform.engine.models.processes.ProcessManager

These modules will be refactored in the future.
"""

from typing import Dict, NamedTuple, Optional, Union
from uuid import UUID

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.managers import WlAppMetadata, get_metadata, update_metadata
from paas_wl.bk_app.applications.models import Build, WlApp
from paas_wl.bk_app.processes.models import ProcessSpec
from paasng.platform.applications.models import ModuleEnvironment


class CreatedAppInfo(NamedTuple):
    uuid: UUID
    name: str
    type: WlAppType


def create_app_ignore_duplicated(region: str, name: str, type_: WlAppType, tenant_id: str) -> CreatedAppInfo:
    """Create an WlApp object, if the object already exists, return it directly.

    :raise RuntimeError: If the app already exists with different properties.
    """
    obj, created = WlApp.objects.get_or_create(
        name=name, defaults={"type": type_.value, "region": region, "tenant_id": tenant_id}
    )
    # If the object already exists, check the properties
    if not created and ((obj.type, obj.region, obj.tenant_id) != (type_.value, region, tenant_id)):
        # This should not happen in normal cases
        raise RuntimeError(f"WlApp {name} already exists with different properties")
    return CreatedAppInfo(obj.uuid, obj.name, WlAppType(obj.type))


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
    from paas_wl.bk_app.deploy.actions.delete import delete_env_resources

    delete_env_resources(env)

    wl_app = env.wl_app
    # Delete some related records manually. Because during API migration, those related data
    # was stored in another database and the `Foreignkey` mechanism can't handle this situation.
    # TODO: Remove below lines when data was fully migrated
    ProcessSpec.objects.filter(engine_app_id=wl_app.pk).delete()
    wl_app.delete()


def get_latest_build(env: ModuleEnvironment) -> Optional[Build]:
    """Get the latest build in the given environment

    :return: `None` if no builds can be found
    """
    try:
        return Build.objects.filter(app=env.wl_app).latest("created")
    except Build.DoesNotExist:
        return None


def get_latest_build_id(env: ModuleEnvironment) -> Optional[UUID]:
    """Get UUID of the latest build in the given environment

    :return: `None` if no builds can be found
    """
    if build := get_latest_build(env):
        return build.pk
    return None
