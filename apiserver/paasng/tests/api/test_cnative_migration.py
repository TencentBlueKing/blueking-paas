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

from unittest import mock

import pytest
from django.utils.crypto import get_random_string
from django_dynamic_fixture import G
from kubernetes.dynamic import ResourceField

from paas_wl.bk_app.applications.managers.app_metadata import update_metadata
from paas_wl.bk_app.processes.controllers import ProcessesInfo
from paas_wl.bk_app.processes.entities import Status
from paas_wl.bk_app.processes.kres_entities import Instance
from paas_wl.infras.cluster.models import Cluster
from paas_wl.workloads.networking.egress.models import RCStateAppBinding, RegionClusterState
from paasng.platform.mgrlegacy.cnative_migrations.wl_app import WlAppBackupManager
from paasng.platform.mgrlegacy.constants import CNativeMigrationStatus
from paasng.platform.mgrlegacy.entities import MigrationResult, ProcessDetails
from paasng.platform.mgrlegacy.models import CNativeMigrationProcess
from tests.conftest import CLUSTER_NAME_FOR_TESTING
from tests.paas_wl.bk_app.processes.test_controllers import make_process

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestMigrateCNativeMigrationViewSet:
    def test_migrate(self, api_client, bk_app):
        with mock.patch("paasng.platform.mgrlegacy.tasks.migrate_default_to_cnative.delay") as mock_task, mock.patch(
            "paasng.platform.mgrlegacy.views.CNativeMigrationViewSet._can_migrate_or_raise"
        ):
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
            app=bk_app,
            owner=bk_user.pk,
            status=CNativeMigrationStatus.MIGRATION_SUCCEEDED.value,
            details=ProcessDetails(
                migrations=[
                    MigrationResult(
                        migrator_name="ApplicationTypeMigrator", is_succeeded=False, error_msg="invalid app type"
                    ),
                ],
            ),
        )
        response = api_client.get(f"/api/mgrlegacy/cloud-native/migration_processes/{process.id}/")
        assert response.data["status"] == "migration_succeeded"
        assert response.data["id"] == process.id
        assert response.data["error_msg"] == ""
        assert response.data["is_active"] is False
        assert response.data["details"]["migrations"][0]["migrator_name"] == "ApplicationTypeMigrator"

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
    @pytest.mark.parametrize(
        ("has_app_permission", "status_code"),
        [(False, 403), (True, 204)],
    )
    def test_confirm(self, api_client, bk_app, bk_user, has_app_permission, status_code):
        with mock.patch(
            "paasng.infras.accounts.permissions.application.user_has_app_action_perm", return_value=has_app_permission
        ):
            process = CNativeMigrationProcess.objects.create(
                app=bk_app, owner=bk_user.pk, status=CNativeMigrationStatus.MIGRATION_SUCCEEDED.value
            )
            response = api_client.put(f"/api/mgrlegacy/cloud-native/migration_processes/{process.id}/confirm/")
            assert response.status_code == status_code

    def test_confirm_failed(self, api_client, bk_app, bk_user):
        process = CNativeMigrationProcess.objects.create(
            app=bk_app, owner=bk_user.pk, status=CNativeMigrationStatus.MIGRATION_FAILED.value
        )
        response = api_client.put(f"/api/mgrlegacy/cloud-native/migration_processes/{process.id}/confirm/")
        assert response.data["detail"] == "应用迁移确认失败: 该应用记录未表明应用已成功迁移, 无法确认"


class TestDefaultAppProcessViewSet:
    @pytest.fixture()
    def wl_app(self, bk_app, _with_wl_apps, bk_stag_env):
        return bk_app.get_engine_app("stag", module_name="default").to_wl_obj()

    @pytest.fixture(autouse=True)
    def _mock_get_wl_app(self, wl_app, bk_stag_env):
        update_metadata(wl_app, module_name="default")
        WlAppBackupManager(bk_stag_env).create()

    @pytest.fixture()
    def processes_info(self, wl_app):
        process = make_process(wl_app, "web")
        process.metadata = ResourceField({"resourceVersion": "1", "name": "test"})
        process.status = Status(replicas=1, success=1, failed=0)
        process.instances = [Instance(wl_app, name="test", process_type="web")]
        return ProcessesInfo(processes=[process], rv_proc="282906629", rv_inst="282906629")

    def test_list(self, api_client, bk_app, processes_info):
        with mock.patch("paasng.platform.mgrlegacy.views.get_processes_info", return_value=processes_info):
            response = api_client.get(
                f"/api/mgrlegacy/applications/{bk_app.code}/modules/default/envs/stag/processes/"
            )
            assert response.data["processes"]["items"][0]["type"] == "web"

    def test_update(self, api_client, bk_app):
        with mock.patch("paasng.platform.mgrlegacy.views.ProcessesHandler.new_by_app") as mock_new:
            handler = mock.MagicMock()
            mock_new.return_value = handler

            response = api_client.put(
                f"/api/mgrlegacy/applications/{bk_app.code}/modules/default/envs/stag/processes/",
                data={"process_type": "web", "operate_type": "stop"},
            )
            handler.shutdown.assert_called()
            assert response.status_code == 204


class TestDefaultAppEntranceViewSet:
    @pytest.fixture(autouse=True)
    def _save_entrances(self, bk_app, bk_user):
        process = CNativeMigrationProcess.objects.create(
            app=bk_app, owner=bk_user.pk, status=CNativeMigrationStatus.MIGRATION_SUCCEEDED.value
        )
        process.legacy_data.entrances = [
            {
                "name": "default",
                "is_default": True,
                "envs": {
                    "stag": [
                        {
                            "address": {"id": 1, "type": "subdomain", "url": "http://app.stag.example.com"},
                            "module": "default",
                            "is_running": True,
                            "env": "stag",
                        }
                    ],
                    "prod": [
                        {
                            "address": {"id": 2, "type": "subdomain", "url": "http://app.prod.example.com"},
                            "module": "default",
                            "is_running": True,
                            "env": "prod",
                        }
                    ],
                },
            }
        ]
        process.save(update_fields=["legacy_data"])

    def test_list_all_entrances(self, api_client, bk_app):
        response = api_client.get(f"/api/mgrlegacy/applications/{bk_app.code}/entrances/")
        assert response.status_code == 200


class TestChecklistInfoViewSet:
    @pytest.fixture()
    def _set_default_cluster(self, settings, bk_app):
        # Create the second cluster
        cluster_name = get_random_string(6)
        G(Cluster, name=cluster_name, region=bk_app.region)
        settings.MGRLEGACY_CLOUD_NATIVE_TARGET_CLUSTER = cluster_name

    @pytest.fixture(autouse=True)
    def _set_rcs_binding(self, _set_default_cluster, settings, bk_app, _with_wl_apps, bk_stag_env):
        wl_app = bk_app.get_engine_app("stag", module_name="default").to_wl_obj()
        state = RegionClusterState.objects.create(
            cluster_name=CLUSTER_NAME_FOR_TESTING,
            nodes_data=[
                {
                    "metadata": {"name": "node-a"},
                    "status": {"addresses": [{"address": "127.0.0.1", "type": "InternalIP"}]},
                }
            ],
        )
        RCStateAppBinding.objects.create(app=wl_app, state=state)

        RegionClusterState.objects.create(
            cluster_name=settings.MGRLEGACY_CLOUD_NATIVE_TARGET_CLUSTER,
            nodes_data=[
                {
                    "metadata": {"name": "node-b"},
                    "status": {"addresses": [{"address": "192.168.0.1", "type": "InternalIP"}]},
                }
            ],
        )

    def test_get(self, api_client, bk_app):
        response = api_client.get(f"/api/mgrlegacy/applications/{bk_app.code}/checklist_info/")
        assert response.status_code == 200
        assert response.data["namespaces"] is None
        assert response.data["rcs_bindings"]["legacy"][0]["ip_addresses"] == ["127.0.0.1"]
        assert response.data["rcs_bindings"]["cnative"]["ip_addresses"] == ["192.168.0.1"]
