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
import logging
from dataclasses import asdict
from itertools import groupby
from operator import attrgetter
from typing import TYPE_CHECKING, Dict, List

from django.utils.translation import gettext_lazy as _

from paasng.engine.constants import ConfigVarEnvName
from paasng.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.core.storages.sqlalchemy import console_db
from paasng.platform.mgrlegacy.app_migrations.base import BaseMigration
from paasng.publish.sync_market.constant import EnvItem
from paasng.publish.sync_market.managers import AppEnvVarManger

if TYPE_CHECKING:
    from paasng.platform.applications.models import ApplicationEnvironment


logger = logging.getLogger(__name__)


class BaseEnvironmentVariableMigration(BaseMigration):
    def get_description(self):
        return _("同步环境变量")

    def _get_environment(self, environment_name: str):
        return self.context.app.envs.get(environment=environment_name)

    def _add_environment_variable(self, variables: List[EnvItem], environment: 'ApplicationEnvironment' = None):
        data = []
        for v in variables:
            var = asdict(v)
            for module in self.context.app.modules.all():
                var.pop('environment_name', None)
                kwargs = {"module": module, "is_global": bool(environment is None), **var}
                if environment is not None:
                    kwargs['environment'] = environment
                else:
                    kwargs['environment_id'] = ENVIRONMENT_ID_FOR_GLOBAL

                data.append(ConfigVar(**kwargs))
        ConfigVar.objects.bulk_create(data)

    def get_global_envs(self):
        raise NotImplementedError

    def get_stag_envs(self):
        raise NotImplementedError

    def get_prod_envs(self):
        raise NotImplementedError

    def get_custom_envs(self) -> List[EnvItem]:
        """用户自定义环境变量"""
        session = console_db.get_scoped_session()
        return AppEnvVarManger(session).list(self.legacy_app.code)

    def transform_system_envs(self, evns: Dict) -> List[EnvItem]:
        # 系统的环境变量都是内置环境变量
        return [EnvItem(key=k, value=v, description='', is_builtin=True) for k, v in evns.items()]

    def handle_env(self):
        custom_env_list = self.get_custom_envs()
        # 自定义变量按环境分类，方便后续一起写入
        sorted_custom_envs = sorted(custom_env_list, key=lambda x: (x.environment_name or ''))
        custom_env_group = groupby(sorted_custom_envs, key=attrgetter('environment_name'))

        custom_env_dict = {k: list(g) for k, g in custom_env_group}

        for env_choice in ConfigVarEnvName.get_choices():
            env_name = env_choice[0]
            if env_name == ConfigVarEnvName.STAG.value:
                config_envs = self.get_stag_envs()
            elif env_name == ConfigVarEnvName.PROD.value:
                config_envs = self.get_prod_envs()
            else:
                config_envs = self.get_global_envs()

            # 环境变量包含系统环境变量和用户自定义环境变量
            envs = self.transform_system_envs(config_envs) + custom_env_dict.get(env_name, [])
            if not envs:
                continue

            # 将环境变量保存到 db 中
            if env_name == ConfigVarEnvName.GLOBAL.value:
                environment = None
            else:
                environment = self._get_environment(env_name)
            self._add_environment_variable(variables=envs, environment=environment)
        return None

    def migrate(self):
        self.handle_env()

    def rollback(self):
        if self.context.app is not None:
            for module in self.context.app.modules.all():
                ConfigVar.objects.filter(module=module).delete()


try:
    # Load external envs
    from . import envs_ext  # type: ignore  # noqa
except ImportError:
    pass
