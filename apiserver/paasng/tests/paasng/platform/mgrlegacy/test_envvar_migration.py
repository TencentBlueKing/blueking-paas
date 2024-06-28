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

import pytest

from paasng.infras.legacydb.entities import EnvItem
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.mgrlegacy.app_migrations.basic import BaseObjectMigration, MainInfoMigration
from paasng.platform.mgrlegacy.app_migrations.envs_base import BaseEnvironmentVariableMigration
from paasng.platform.mgrlegacy.app_migrations.product import ProductMigration
from tests.paasng.platform.mgrlegacy.test_migration import BaseMigrationTest

try:
    from paasng.platform.mgrlegacy.app_migrations.sourcectl_te import SourceControlMigration
except ImportError:
    from paasng.platform.mgrlegacy.app_migrations.sourcectl import SourceControlMigration

pytestmark = pytest.mark.django_db


class TestBaseEnvironmentVariableMigration(BaseMigrationTest):
    MIGRATION_CLS = BaseEnvironmentVariableMigration
    PRECONDITION_MIGRATION_CLS = [BaseObjectMigration, MainInfoMigration, SourceControlMigration, ProductMigration]

    migration: BaseEnvironmentVariableMigration

    def test_migrate(self, migration, context):
        stag_env = context.app.envs.get(environment="stag")
        prod_env = context.app.envs.get(environment="prod")

        env_list = [
            dict(GLOBAL_ENV_STUB="stub", CONFLICT_ENV="global"),
            dict(STAG_ENV_STUB="stub", CONFLICT_ENV="stag"),
            dict(PROD_ENV_STUB="stub", CONFLICT_ENV="prod"),
        ]

        kwargs_list = [
            dict(environment_id=ENVIRONMENT_ID_FOR_GLOBAL),
            dict(environment=stag_env),
            dict(environment=prod_env),
        ]
        migration.get_global_envs = lambda: env_list[0]  # type: ignore
        migration.get_stag_envs = lambda: env_list[1]  # type: ignore
        migration.get_prod_envs = lambda: env_list[2]  # type: ignore
        # 自定义环境变量，有很多方法需要 implement，所以没有把自定义环境变量放到单独的单元测试中
        custom_env_list = [
            EnvItem(key="STAG_ENV", value="stag", description="", is_builtin=False, environment_name="stag"),
            EnvItem(key="PROD_ENV", value="prod", description="", is_builtin=False, environment_name="prod"),
            EnvItem(
                key="GLOBAL_ENV",
                value="_global_",
                description="这是一个的描述",
                is_builtin=False,
                environment_name="_global_",
            ),
        ]
        migration.get_custom_envs = lambda: custom_env_list  # type: ignore
        migration.migrate()
        for module in context.app.modules.all():
            # 验证系统环境变量
            for i, kwargs in enumerate(kwargs_list):
                for env in ConfigVar.objects.filter(module=module, is_builtin=True, **kwargs).all():
                    key = env.key
                    value = env.value
                    assert env_list[i].get(key) == value, "环境变量配置错误"

            # 验证自定义环境变量
            config_vars = ConfigVar.objects.filter(module=module, is_builtin=False).all()
            assert config_vars.count() == len(custom_env_list)

    def test_rollback(self, migration, context):
        self.test_migrate(migration, context)
        migration.rollback()
        for module in context.app.modules.all():
            assert ConfigVar.objects.filter(module=module).count() == 0, "环境变量未完全删除"
