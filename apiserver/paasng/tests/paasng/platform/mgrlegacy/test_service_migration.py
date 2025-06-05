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

import uuid
from unittest import mock

import pytest

from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import (
    RemoteServiceEngineAppAttachment,
    RemoteServiceModuleAttachment,
)
from paasng.accessories.servicehub.remote.manager import RemotePlanObj, RemoteServiceObj
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.mgrlegacy.app_migrations.service import BaseRemoteServiceMigration, BaseServiceMigration
from tests.conftest import skip_if_legacy_not_configured

pytestmark = [
    skip_if_legacy_not_configured(),
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.xdist_group(name="remote-services"),
]


dummy_service = RemoteServiceObj(
    uuid="00000000-0000-0000-0000-000000000000",
    name="dummy-service",
    logo="",
    is_visible=True,
    plans=[
        RemotePlanObj(
            uuid="11111111-1111-1111-1111-111111111111",
            tenant_id=DEFAULT_TENANT_ID,
            name="dummy-plan",
            description="dummy plan",
            is_eager=True,
            is_active=True,
            properties={},
        )
    ],
)


@pytest.fixture(autouse=True)
def _mock_get_service():
    with mock.patch.object(BaseServiceMigration, "get_service") as get_service:
        get_service.return_value = dummy_service
        with mock.patch.object(mixed_service_mgr, "get") as get:
            get.return_value = dummy_service
            SvcBindingPolicyManager(dummy_service, DEFAULT_TENANT_ID).set_uniform(
                plans=[dummy_service.get_plans()[0].uuid]
            )
        yield


class TestBaseServiceMigration:
    def test_get_service(self, migration_instance_maker):
        assert migration_instance_maker(BaseServiceMigration).get_service() is dummy_service


class TestBaseRemoteServiceMigration:
    def test_bind_service_to_default_module(self, bk_module, migration_instance_maker):
        migration = migration_instance_maker(BaseRemoteServiceMigration)
        assert RemoteServiceModuleAttachment.objects.filter(module=bk_module).exists() is False
        migration.bind_service_to_default_module()
        assert RemoteServiceModuleAttachment.objects.filter(module=bk_module).exists() is True
        for env in bk_module.envs.all():
            assert RemoteServiceEngineAppAttachment.objects.filter(engine_app=env.engine_app).exists() is False

    def test_bind_default_plan_as_fallback(self, bk_module, migration_instance_maker):
        migration = migration_instance_maker(BaseRemoteServiceMigration)
        migration.bind_service_to_default_module()

        for env in bk_module.envs.all():
            assert RemoteServiceEngineAppAttachment.objects.filter(engine_app=env.engine_app).exists() is False

        migration.bind_default_plan_as_fallback()

        for env in list(AppEnvName):
            attachment = migration.get_engine_app_attachment(env)
            assert attachment.plan_id == uuid.UUID("{11111111-1111-1111-1111-111111111111}")

    def test_get_engine_app_attachment(self, migration_instance_maker):
        migration = migration_instance_maker(BaseRemoteServiceMigration)
        migration.bind_service_to_default_module()

        for env in list(AppEnvName):
            attachment = migration.get_engine_app_attachment(env)
            assert attachment.plan_id == uuid.UUID("{00000000-0000-0000-0000-000000000000}")

    def test_rollback_service_instance(self, bk_module, migration_instance_maker):
        migration = migration_instance_maker(BaseRemoteServiceMigration)
        migration.bind_service_to_default_module()
        migration.bind_default_plan_as_fallback()

        with mock.patch(
            "paasng.platform.mgrlegacy.app_migrations.service.RemotePlainInstanceMgr.get_remote_client"
        ) as mocked:
            for env in list(AppEnvName):
                migration.rollback_service_instance(env)

            assert mocked.called

        assert RemoteServiceModuleAttachment.objects.filter(module=bk_module).exists() is True
        assert (
            RemoteServiceEngineAppAttachment.objects.filter(
                engine_app__in=bk_module.envs.values_list("engine_app", flat=True)
            ).exists()
            is False
        )
