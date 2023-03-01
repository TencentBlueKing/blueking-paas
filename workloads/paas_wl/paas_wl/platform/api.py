"""Provide functions for the apiserver module.

- Functions should be as few as possible
- Do not return the models in workloads directly when a simple data class is sufficient

Other modules which have similar purpose:

- paasng.engine.deploy.engine_svc.EngineDeployClient
- paasng.engine.models.processes.ProcessManager

These modules will be refactored in the future.
"""
from typing import NamedTuple
from uuid import UUID

from django.db.utils import IntegrityError

from paas_wl.platform.applications.models.app import WLEngineApp


class CreatedAppInfo(NamedTuple):
    uuid: UUID
    name: str


def create_app_ignore_duplicated(region: str, name: str, type_: str) -> CreatedAppInfo:
    """Create an engine app object, return directly if the object already exists"""
    try:
        obj = WLEngineApp.objects.create(region=region, name=name, type=type_)
    except IntegrityError:
        obj = WLEngineApp.objects.get(region=region, name=name)
    return CreatedAppInfo(obj.uuid, obj.name)
