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
from typing import TYPE_CHECKING, Dict

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from paasng.engine.constants import ConfigVarEnvName
from paasng.utils.models import TimestampedModel

if TYPE_CHECKING:
    from paasng.platform.modules.models.module import Module

ENVIRONMENT_ID_FOR_GLOBAL = -1
ENVIRONMENT_NAME_FOR_GLOBAL = ConfigVarEnvName.GLOBAL.value
CONFIG_VAR_INPUT_FIELDS = ['is_global', 'environment_id', 'key', 'value', 'description']


def get_config_vars(module: 'Module', env_name: str) -> Dict[str, str]:
    """Get ConfigVars of module as dict, config vars priority: builtin/not global/global

    :param str env_name: environment name, such as 'prod'
    :returns: Dict of config vars
    """
    try:
        env_id = module.envs.get(environment=env_name).pk
    except ObjectDoesNotExist:
        raise ValueError('Invalid env_name given: %s' % env_name)

    config_vars = ConfigVar.objects.filter(
        module=module, environment_id__in=(ENVIRONMENT_ID_FOR_GLOBAL, env_id)
    ).order_by('environment_id')
    return {obj.key: obj.value for obj in config_vars}


class ConfigVarQuerySet(models.QuerySet):
    """Custom QuerySet for ConfigVar model"""

    def filter_by_environment_name(self, name: ConfigVarEnvName):
        """Filter ConfigVar objects by environment name"""
        if name == ConfigVarEnvName.GLOBAL:
            return self.filter(environment_id=ENVIRONMENT_ID_FOR_GLOBAL)
        return self.filter(environment__environment=name.value)


class ConfigVar(TimestampedModel):
    """Config vars for application"""

    module = models.ForeignKey('modules.Module', on_delete=models.CASCADE, null=True)

    is_global = models.BooleanField(default=False)
    # When is_global is True, environment_id will be set to -1, because null value will break
    # MySQL unique index, see: https://stackoverflow.com/questions/1346765/unique-constraint-that-allows-empty-values-in-mysql # noqa
    environment = models.ForeignKey(
        'applications.ApplicationEnvironment', on_delete=models.CASCADE, db_constraint=False, null=True
    )

    key = models.CharField(max_length=128, null=False)
    value = models.TextField(null=False)
    description = models.CharField(max_length=200, null=True)
    is_builtin = models.BooleanField(default=False)

    objects = ConfigVarQuerySet.as_manager()

    class Meta:
        unique_together = ('module', 'is_global', 'environment', 'key')

    def __str__(self):
        return "{var_name}-{var_value}-{app_code}".format(
            var_name=self.key, var_value=self.value, app_code=self.module.application.code
        )

    @property
    def environment_name(self):
        if self.environment_id == ENVIRONMENT_ID_FOR_GLOBAL:
            return ConfigVarEnvName.GLOBAL.value
        return ConfigVarEnvName(self.environment.environment).value

    def is_equivalent_to(self, other: 'ConfigVar') -> bool:
        """Determine whether the two ConfigVars are equivalent.

        Equivalent is meaning that the tow quadruple(key, value, description, environment_name) are all equal.

        :param other: the other ConfigVar
        :return: are equivalent or not
        """
        return (self.key, self.value, self.description, self.environment_name) == (
            other.key,
            other.value,
            other.description,
            self.environment_name,
        )

    def clone_to(self, module: 'Module') -> 'ConfigVar':
        """Make a copy ConfigVar, but linking to the module in params."""
        if self.environment_id == ENVIRONMENT_ID_FOR_GLOBAL:
            environment_id = ENVIRONMENT_ID_FOR_GLOBAL
        else:
            environment_id = module.get_envs(self.environment.environment).id

        return ConfigVar(
            key=self.key,
            value=self.value,
            description=self.description,
            is_global=self.is_global,
            is_builtin=self.is_builtin,
            # 差异点
            environment_id=environment_id,
            module=module,
        )


def add_prefix_to_key(items: dict, prefix: str) -> Dict[str, str]:
    return {f"{prefix}{key}": value for key, value in items.items()}
