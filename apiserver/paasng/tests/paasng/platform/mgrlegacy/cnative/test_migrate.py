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
from unittest import mock

import pytest

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.mgrlegacy.cnative_migrations.build_config import BuildConfigMigrator
from paasng.platform.mgrlegacy.migrate import migrate_default_to_cnative, rollback_cnative_to_default
from paasng.platform.mgrlegacy.task_data import MIGRATE_TO_CNATIVE_CLASSES_LIST
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.modules.models import BuildConfig
from tests.conftest import CLUSTER_NAME_FOR_TESTING

from .conftest import CNATIVE_CLUSTER_NAME

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestMigrateAndRollback:
    @pytest.fixture()
    def _init_build_config(self, bk_app, bk_module, _init_runtime):
        module_initializer = ModuleInitializer(bk_module)
        module_initializer.bind_default_runtime()

    @pytest.mark.usefixtures("_init_build_config")
    def test_migrate_and_rollback(self, bk_app, bk_module, migration_process, rollback_process, cnb_builder):
        migrate_default_to_cnative(migration_process)
        assert [result.migrator_name for result in migration_process.details.migrations] == [
            migrator_cls.get_name() for migrator_cls in MIGRATE_TO_CNATIVE_CLASSES_LIST
        ]
        assert migration_process.status == "migration_succeeded"
        assert bk_app.type == ApplicationType.CLOUD_NATIVE.value
        assert bk_app.get_engine_app("stag").to_wl_obj().latest_config.cluster == CNATIVE_CLUSTER_NAME
        assert [result.migrator_name for result in migration_process.details.migrations] == [
            "ApplicationTypeMigrator",
            "BoundClusterMigrator",
            "BuildConfigMigrator",
        ]

        config = BuildConfig.objects.get(module=bk_module)
        assert config.buildpack_builder == cnb_builder

        rollback_cnative_to_default(rollback_process, migration_process)
        assert rollback_process.status == "rollback_succeeded"
        assert [result.migrator_name for result in rollback_process.details.rollbacks] == [
            "ApplicationTypeMigrator",
            "BoundClusterMigrator",
            "BuildConfigMigrator",
        ]

    def test_migrate_failed(self, bk_app, migration_process):
        """test migrate failed when BuildConfigMigrator migrate failed"""
        with mock.patch.object(BuildConfigMigrator, "_generate_legacy_data") as mock_method:
            mock_method.side_effect = Exception("generate wrong")

            migrate_default_to_cnative(migration_process)

            assert migration_process.status == "migration_failed"
            assert bk_app.type == ApplicationType.DEFAULT.value
            assert bk_app.get_engine_app("stag").to_wl_obj().latest_config.cluster == CLUSTER_NAME_FOR_TESTING

            assert [result.migrator_name for result in migration_process.details.migrations] == [
                "ApplicationTypeMigrator",
                "BoundClusterMigrator",
                "BuildConfigMigrator",
            ]
            assert [result.migrator_name for result in migration_process.details.rollbacks] == [
                "ApplicationTypeMigrator",
                "BoundClusterMigrator",
            ]
