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
from django.core.exceptions import ObjectDoesNotExist

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.mgrlegacy.cnative_migrations.application import ApplicationTypeMigrator
from paasng.platform.mgrlegacy.cnative_migrations.build_config import BuildConfigMigrator
from paasng.platform.mgrlegacy.cnative_migrations.cluster import ApplicationClusterMigrator
from paasng.platform.mgrlegacy.cnative_migrations.wl_app import WlAppBackupManager, WlAppBackupMigrator
from paasng.platform.mgrlegacy.models import WlAppBackupRel
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.modules.models import BuildConfig
from paasng.platform.modules.models.module import Module
from paasng.platform.sourcectl.docker.models import get_or_create_repo_obj
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

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

    @pytest.fixture()
    def image_repository_module(self, bk_app):
        repo_obj = get_or_create_repo_obj(bk_app, "docker", "https://example.com/image", ".")
        return Module.objects.create(
            application=bk_app,
            name="image-repository",
            region=bk_app.region,
            owner=bk_app.owner,
            creator=bk_app.creator,
            source_origin=SourceOrigin.IMAGE_REGISTRY.value,
            source_type="docker",
            source_repo_id=repo_obj.id,
        )

    def test_migrate_and_rollback(
        self,
        bk_app,
        bk_module,
        image_repository_module,
        migration_process,
        cnb_builder,
        cnb_runner,
        buildpack,
        slugbuilder,
        slugrunner,
    ):
        BuildConfigMigrator(migration_process).migrate()
        config = BuildConfig.objects.get(module=bk_module)
        assert config.buildpacks.filter(id=buildpack.id).exists()
        assert config.buildpack_builder == cnb_builder
        assert config.buildpack_runner == cnb_runner

        image_config = BuildConfig.objects.get(module=image_repository_module)
        assert image_config.image_repository == "https://example.com/image"
        assert image_config.build_method == RuntimeType.CUSTOM_IMAGE.value
        assert Module.objects.get(id=image_repository_module.id).source_origin == SourceOrigin.CNATIVE_IMAGE.value

        BuildConfigMigrator(migration_process).rollback()
        config = BuildConfig.objects.get(module=bk_module)
        assert config.buildpacks.filter(id=buildpack.id).exists()
        assert config.buildpack_builder == slugbuilder
        assert config.buildpack_runner == slugrunner

        image_config = BuildConfig.objects.get(module=image_repository_module)
        assert image_config.image_repository is None
        legacy_image_repository_module = Module.objects.get(id=image_repository_module.id)
        assert legacy_image_repository_module.source_origin == SourceOrigin.IMAGE_REGISTRY.value
        assert legacy_image_repository_module.get_source_obj().get_repo_url() == "https://example.com/image"
