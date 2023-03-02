"""Provide functions for the apiserver module.

- Functions should be as few as possible
- Do not return the models in workloads directly when a simple data class is sufficient

Other modules which have similar purpose:

- paasng.engine.deploy.engine_svc.EngineDeployClient
- paasng.engine.models.processes.ProcessManager

These modules will be refactored in the future.
"""
from typing import Dict, NamedTuple, Union
from uuid import UUID

from paas_wl.platform.applications.models.app import WLEngineApp
from paas_wl.platform.applications.models.managers.app_metadata import EngineAppMetadata, get_metadata, update_metadata
from paas_wl.resources.actions.delete import delete_app_resources
from paas_wl.workloads.processes.models import ProcessSpec
from paasng.platform.applications.models import ModuleEnvironment


class CreatedAppInfo(NamedTuple):
    uuid: UUID
    name: str


def create_app_ignore_duplicated(region: str, name: str, type_: str) -> CreatedAppInfo:
    """Create an engine app object, return directly if the object already exists"""
    try:
        obj = WLEngineApp.objects.get(region=region, name=name)
    except WLEngineApp.DoesNotExist:
        obj = WLEngineApp.objects.create(region=region, name=name, type=type_)
    return CreatedAppInfo(obj.uuid, obj.name)


def get_metadata_by_env(env: ModuleEnvironment) -> EngineAppMetadata:
    """Get an environment's metadata"""
    wl_app = WLEngineApp.objects.get(pk=env.engine_app_id)
    return get_metadata(wl_app)


def update_metadata_by_env(env: ModuleEnvironment, metadata_part: Dict[str, Union[str, bool]]):
    """Update an environment's metadata, works like python's dict.update()

    :param metadata_part: An dict object which will be merged into app's metadata
    """
    wl_app = WLEngineApp.objects.get(pk=env.engine_app_id)
    update_metadata(wl_app, **metadata_part)


def delete_wl_resources(env: ModuleEnvironment):
    """Delete all resources of the given environment in workloads module, this function
    should be called when user deletes an application/module/env.

    :param env: Environment object.
    """
    wl_app = env.engine_app.to_wl_obj()
    delete_app_resources(wl_app)

    # Delete some related records manually. Because during API migration, those related data
    # was stored in another database and the `Foreignkey` mechanism can't handle this situation.
    # TODO: Remove below lines when data was fully migrated
    ProcessSpec.objects.filter(engine_app_id=wl_app.pk).delete()

    wl_app.delete()
