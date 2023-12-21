import datetime
import uuid
from typing import Dict, Iterable

from typing_extensions import TypeAlias

from paas_wl.bk_app.applications.models.config import Config
from paasng.platform.applications.models import ModuleEnvironment

WlAppId: TypeAlias = uuid.UUID


def get_mapper_v1_envs() -> Iterable[ModuleEnvironment]:
    """Get all environments that use resource mapper "v1" rule.

    :return: An iterable of ModuleEnvironment objects.
    """
    processed: Dict[WlAppId, datetime.datetime] = {}
    version_map: Dict[WlAppId, str] = {}
    for config in Config.objects.all().iterator():
        # Ignore older configs
        if (last_created := processed.get(config.app_id)) and config.created < last_created:
            continue
        processed[config.app_id] = config.created

        m = config.metadata or {}
        if ver := m.get("mapper_version"):
            version_map[config.app_id] = ver

    # Filter and print all envs that use v1
    for app_id, ver in version_map.items():
        if ver != "v1":
            continue
        try:
            env = ModuleEnvironment.objects.get(engine_app_id=app_id)
        except ModuleEnvironment.DoesNotExist:
            continue

        yield env
