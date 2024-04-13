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

from paasng.platform.mgrlegacy.constants import CNativeMigrationStatus
from paasng.platform.mgrlegacy.entities import MigrationResult, ProcessDetails
from paasng.platform.mgrlegacy.models import CNativeMigrationProcess

pytestmark = pytest.mark.django_db


class TestMigrateCNativeMigrationViewSet:
    def test_migrate(self, api_client, bk_app):
        with mock.patch("paasng.platform.mgrlegacy.tasks.migrate_default_to_cnative.delay") as mock_task:
            mock_task.return_value = None

            response = api_client.post(f"/api/mgrlegacy/cloud-native/applications/{bk_app.code}/migrate/")
            assert response.status_code == 201
            assert CNativeMigrationProcess.objects.filter(id=response.data["process_id"]).exists()

    def test_migrate_when_progress_is_active(self, api_client, bk_user, bk_app):
        CNativeMigrationProcess.create_migration_process(bk_app, bk_user.pk)

        response = api_client.post(f"/api/mgrlegacy/cloud-native/applications/{bk_app.code}/migrate/")
        assert response.status_code == 400
        assert response.data["detail"] == "应用迁移失败: 该应用正在变更中, 无法迁移"


class TestRollbackCNativeMigrationViewSet:
    def test_rollback(self, api_client, bk_cnative_app, bk_user):
        CNativeMigrationProcess.objects.create(
            app=bk_cnative_app, owner=bk_user.pk, status=CNativeMigrationStatus.MIGRATION_SUCCEEDED.value
        )

        with mock.patch("paasng.platform.mgrlegacy.tasks.rollback_cnative_to_default.delay") as mock_task:
            mock_task.return_value = None

            response = api_client.post(f"/api/mgrlegacy/cloud-native/applications/{bk_cnative_app.code}/rollback/")
            assert response.status_code == 201
            assert CNativeMigrationProcess.objects.filter(id=response.data["process_id"]).exists()

    def test_rollback_when_last_migration_failed(self, api_client, bk_user, bk_cnative_app):
        CNativeMigrationProcess.objects.create(
            app=bk_cnative_app, owner=bk_user.pk, status=CNativeMigrationStatus.MIGRATION_FAILED.value
        )

        response = api_client.post(f"/api/mgrlegacy/cloud-native/applications/{bk_cnative_app.code}/rollback/")
        assert response.status_code == 400
        assert response.data["detail"] == "应用回滚失败: 该应用处于 migration_failed 状态, 无法回滚"

    def test_rollback_when_never_migrated(self, api_client, bk_user, bk_cnative_app):
        response = api_client.post(f"/api/mgrlegacy/cloud-native/applications/{bk_cnative_app.code}/rollback/")
        assert response.status_code == 400
        assert response.data["detail"] == "应用回滚失败: 该应用未进行过迁移, 无法回滚"


class TestQueryProcessCNativeMigrationViewSet:
    def test_get_process_by_id(self, api_client, bk_app, bk_user):
        process = CNativeMigrationProcess.objects.create(
            app=bk_app, owner=bk_user.pk, status=CNativeMigrationStatus.MIGRATION_SUCCEEDED.value
        )
        response = api_client.get(f"/api/mgrlegacy/cloud-native/migration_processes/{process.id}/")
        assert response.data["status"] == "migration_succeeded"
        assert response.data["error_msg"] == ""

    def test_get_process_by_id_404(self, api_client, bk_app, bk_user):
        response = api_client.get("/api/mgrlegacy/cloud-native/migration_processes/1/")
        assert response.status_code == 404

    def test_get_latest_process(self, api_client, bk_app, bk_user):
        CNativeMigrationProcess.objects.create(
            app=bk_app,
            owner=bk_user.pk,
            status=CNativeMigrationStatus.DEFAULT.value,
        )
        CNativeMigrationProcess.objects.create(
            app=bk_app,
            owner=bk_user.pk,
            status=CNativeMigrationStatus.MIGRATION_SUCCEEDED.value,
        )

        response = api_client.get(
            f"/api/mgrlegacy/cloud-native/applications/{bk_app.code}/migration_processes/latest/"
        )
        assert response.data["status"] == "migration_succeeded"

    def list_processes(self, api_client, bk_app, bk_user):
        migrations = [
            MigrationResult(migrator_name="ApplicationTypeMigrator", is_successful=True),
            MigrationResult(migrator_name="BoundClusterMigrator", is_successful=True),
            MigrationResult(
                migrator_name="BuildConfigMigrator",
                is_successful=False,
                is_finished=True,
                error_msg="cnb buildpacks versions incompatible",
            ),
        ]
        CNativeMigrationProcess.objects.create(
            app=bk_app,
            owner=bk_user.pk,
            status=CNativeMigrationStatus.MIGRATION_FAILED.value,
            details=ProcessDetails(migrations=migrations),
        )
        CNativeMigrationProcess.objects.create(
            app=bk_app, owner=bk_user.pk, status=CNativeMigrationStatus.MIGRATION_SUCCEEDED.value
        )

        response = api_client.get(f"/api/mgrlegacy/cloud-native/applications/{bk_app.code}/migration_processes/")
        assert response.data[0]["status"] == "migration_succeeded"
        assert response.data[1]["status"] == "migration_failed"
        assert response.data[1]["error_msg"] == "cnb buildpacks versions incompatible"


class TestConfirmCNativeMigrationViewSet:
    def test_confirm(self, api_client, bk_app, bk_user):
        process = CNativeMigrationProcess.objects.create(
            app=bk_app, owner=bk_user.pk, status=CNativeMigrationStatus.MIGRATION_SUCCEEDED.value
        )
        response = api_client.put(f"/api/mgrlegacy/cloud-native/migration_processes/{process.id}/confirm/")
        assert response.status_code == 204

    def test_confirm_failed(self, api_client, bk_app, bk_user):
        process = CNativeMigrationProcess.objects.create(
            app=bk_app, owner=bk_user.pk, status=CNativeMigrationStatus.MIGRATION_FAILED.value
        )
        response = api_client.put(f"/api/mgrlegacy/cloud-native/migration_processes/{process.id}/confirm/")
        assert response.data["detail"] == "应用迁移确认失败: 该应用记录未表明应用已成功迁移, 无法确认"
