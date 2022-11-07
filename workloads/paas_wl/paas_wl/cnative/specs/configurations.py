import copy
from typing import List

from blue_krill.data_types.enum import StructuredEnum
from django.conf import settings

from paas_wl.cnative.specs.v1alpha1.bk_app import EnvVar
from paas_wl.platform.external.client import get_plat_client


def generate_builtin_configurations(code: str, environment: str) -> List[EnvVar]:
    builtin_envs = get_plat_client().list_builtin_envs(code=code, environment=environment)
    return [EnvVar(name="PORT", value=str(settings.CONTAINER_PORT))] + [
        EnvVar(name=name.upper(), value=value) for name, value in builtin_envs.items()
    ]


class MergeStrategy(str, StructuredEnum):
    OVERRIDE = "Override"
    IGNORE = "Ignore"


def merge_envvars(x: List[EnvVar], y: List[EnvVar], strategy: MergeStrategy = MergeStrategy.OVERRIDE):
    """merge envvars x and y, if key conflict, will resolve with given strategy.

    MergeStrategy.OVERRIDE: will use the one in y if x and y have same name EnvVar
    MergeStrategy.IGNORE: will ignore the EnvVar in y if x and y have same name EnvVar
    """
    merged = copy.deepcopy(x)
    y_vars = {var.name: var.value for var in y}
    for var in merged:
        if var.name in y_vars:
            value = y_vars.pop(var.name)
            if strategy == MergeStrategy.OVERRIDE:
                var.value = value
    for name, value in y_vars.items():
        merged.append(EnvVar(name=name, value=value))
    return merged
