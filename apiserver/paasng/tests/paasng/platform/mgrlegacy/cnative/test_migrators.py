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
import pytest
from django.core.exceptions import ObjectDoesNotExist

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.mgrlegacy.cnative_migrations.application import ApplicationTypeMigrator
from paasng.platform.mgrlegacy.cnative_migrations.build_config import BuildConfigMigrator
from paasng.platform.mgrlegacy.cnative_migrations.cluster import ApplicationClusterMigrator
from paasng.platform.mgrlegacy.cnative_migrations.wl_app import WlAppBackupManager, WlAppBackupMigrator
from paasng.platform.mgrlegacy.models import WlAppBackupRel
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.modules.models import BuildConfig
from tests.conftest import CLUSTER_NAME_FOR_TESTING

from .conftest import CNATIVE_CLUSTER_NAME

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestWlAppBackupMigrator:
    def test_migrate_and_rollback(self, bk_app, bk_stag_env, migration_process):
        WlAppBackupMigrator(migration_process).migrate()
        assert WlAppBackupManager(bk_stag_env).get().region == bk_app.region
        assert WlAppBackupRel.objects.get(backup_id=WlAppBackupManager(bk_stag_env).get().uuid)

        WlAppBackupMigrator(migration_process).rollback()
        with pytest.raises(ObjectDoesNotExist):
            WlAppBackupManager(bk_stag_env).get()


class TestApplicationTypeMigrator:
    def test_migrate_and_rollback(self, bk_app, bk_stag_env, migration_process):
        ApplicationTypeMigrator(migration_process).migrate()
        assert bk_app.type == ApplicationType.CLOUD_NATIVE.value
        assert bk_app.get_engine_app("stag").to_wl_obj().type == ApplicationType.CLOUD_NATIVE.value

        ApplicationTypeMigrator(migration_process).rollback()
        assert bk_app.type == ApplicationType.DEFAULT.value
        assert bk_app.get_engine_app("stag").to_wl_obj().type == ApplicationType.DEFAULT.value


class TestApplicationClusterMigrator:
    @pytest.fixture(autouse=True)
    def _migrate_app_type(self, bk_app, migration_process):
        ApplicationTypeMigrator(migration_process).migrate()
        yield
        ApplicationTypeMigrator(migration_process).rollback()

    def test_migrate_and_rollback(self, bk_app, migration_process):
        ApplicationClusterMigrator(migration_process).migrate()
        assert bk_app.get_engine_app("stag").to_wl_obj().latest_config.cluster == CNATIVE_CLUSTER_NAME

        ApplicationClusterMigrator(migration_process).rollback()
        assert bk_app.get_engine_app("stag").to_wl_obj().latest_config.cluster == CLUSTER_NAME_FOR_TESTING


class TestBuildConfigMigrator:
    @pytest.fixture(autouse=True)
    def _init_build_config(self, bk_app, bk_module, _init_runtime):
        module_initializer = ModuleInitializer(bk_module)
        module_initializer.bind_default_runtime()

    @pytest.fixture(autouse=True)
    def _migrate_app_type(self, bk_app, migration_process):
        ApplicationTypeMigrator(migration_process).migrate()
        yield
        ApplicationTypeMigrator(migration_process).rollback()

    def test_migrate_and_rollback(
        self, bk_app, bk_module, migration_process, cnb_builder, cnb_runner, buildpack, slugbuilder, slugrunner
    ):
        BuildConfigMigrator(migration_process).migrate()
        config = BuildConfig.objects.get(module=bk_module)
        assert config.buildpacks.filter(id=buildpack.id).exists()
        assert config.buildpack_builder == cnb_builder
        assert config.buildpack_runner == cnb_runner

        BuildConfigMigrator(migration_process).rollback()
        config = BuildConfig.objects.get(module=bk_module)
        assert config.buildpacks.filter(id=buildpack.id).exists()
        assert config.buildpack_builder == slugbuilder
        assert config.buildpack_runner == slugrunner
