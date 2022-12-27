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
import uuid
from dataclasses import dataclass
from unittest import mock

import pytest
from django.conf import settings

from paas_wl.platform.applications.constants import ApplicationType
from paas_wl.platform.applications.exceptions import AppSubResourceNotFound, UnsupportedPermissionName
from paas_wl.platform.applications.struct_models import (
    Application,
    ApplicationPermissions,
    ModuleAttrFromID,
    ModuleEnvAttrFromID,
    ModuleEnvAttrFromName,
    PermissionsInPlace,
    StructuredApp,
    get_env_by_engine_app_id,
    to_structured,
)
from tests.utils.mocks.platform import FakePlatformSvcClient, make_structured_app_data


@pytest.fixture
def structured_app_data(bk_app):
    """Structured application data with one default module"""
    return make_structured_app_data(bk_app)


@pytest.fixture
def application():
    return Application(
        id=uuid.uuid4(),
        type=ApplicationType.DEFAULT,
        region=settings.FOR_TESTS_DEFAULT_REGION,
        name='foo-app',
        code='foo-app',
    )


class TestApplicationPermissions:
    def test_check_allowed(self, application):
        perms = ApplicationPermissions(application=application, detail={'can_view': False})
        assert perms.check_allowed('can_view') is False

    def test_check_allowed_invalid_name(self, application):
        perms = ApplicationPermissions(application=application, detail={'can_view': True})
        with pytest.raises(UnsupportedPermissionName):
            perms.check_allowed('invalid_name')


class TestPermissionsInPlace:
    def test_normal(self, application):
        perms_in_place = PermissionsInPlace()
        app_perms = ApplicationPermissions(application=application, detail={'can_view': True})
        perms_in_place.application_perms.append(app_perms)
        assert perms_in_place.get_application_perms(application) is not None


class TestStructuredApp:
    def test_from_json(self, structured_app_data):
        obj = StructuredApp.from_json_data(structured_app_data)
        assert len(obj.modules) > 0

    def test_module_ids(self, structured_app_data):
        obj = StructuredApp.from_json_data(structured_app_data)
        assert isinstance(obj.module_ids[0], uuid.UUID)

    def test_integrated(self, structured_app_data):
        obj = StructuredApp.from_json_data(structured_app_data)
        module = obj.get_module_by_name('default')
        assert obj.get_env_by_environment(module, 'stag') is not None

    def test_get_env_by_engine_app_id(self, structured_app_data):
        obj = StructuredApp.from_json_data(structured_app_data)
        assert obj.get_env_by_engine_app_id(obj.module_envs[0].engine_app_id) is not None


@pytest.fixture(autouse=True)
def _setup_clients():
    with mock.patch('paas_wl.platform.external.client._global_plat_client', new=FakePlatformSvcClient()):
        yield


def test_get_env_by_engine_app_id(structured_app_data):
    eid = structured_app_data['envs'][0]['engine_app_id']
    assert get_env_by_engine_app_id(uuid.UUID(eid)) is not None


class TestToStructured:
    def test_normal(self, bk_app):
        struct_app = to_structured(bk_app)
        assert len(struct_app.modules) > 0

    def test_not_found(self, bk_app):
        with pytest.raises(ValueError):
            with FakePlatformSvcClient.query_applications.mock(return_value=[None]):
                _ = to_structured(bk_app)


@dataclass
class FooModule:
    module_id: uuid.UUID
    module = ModuleAttrFromID()


class TestModuleAttrFromID:
    def test_id_not_match(self, bk_app):
        with FakePlatformSvcClient.query_applications.mock(
            return_value=[make_structured_app_data(bk_app, default_module_id=str(uuid.uuid4()))]
        ):
            # Use another UUID as module_id
            obj = FooModule(uuid.uuid4())
            with pytest.raises(AppSubResourceNotFound):
                _ = obj.module

    def test_normal(self, bk_app):
        module_id = uuid.uuid4()
        with FakePlatformSvcClient.query_applications.mock(
            return_value=[make_structured_app_data(bk_app, default_module_id=str(module_id))]
        ):
            obj = FooModule(module_id)

        assert obj.module.id == module_id
        assert obj.module.name == 'default'


@dataclass
class FooEnvModule:
    environment_id: int
    environment = ModuleEnvAttrFromID()


class TestModuleEnvAttrFromID:
    def test_normal(self, bk_app):
        with FakePlatformSvcClient.query_applications.mock(
            return_value=[make_structured_app_data(bk_app, environment_ids=[100, 101])]
        ):
            obj = FooEnvModule(100)

        assert obj.environment.id == 100
        assert obj.environment.environment == 'stag'


@dataclass
class FooEnvNameModule:
    module_id: uuid.UUID
    module = ModuleAttrFromID()
    environment_name: str
    environment = ModuleEnvAttrFromName()


class TestModuleAttrFromName:
    def test_normal(self, bk_app):
        module_id = uuid.uuid4()
        with FakePlatformSvcClient.query_applications.mock(
            return_value=[
                make_structured_app_data(bk_app, default_module_id=str(module_id), environment_ids=[100, 101])
            ]
        ):
            obj = FooEnvNameModule(module_id=module_id, environment_name='prod')

            assert obj.environment.id == 101
            assert obj.environment.environment == 'prod'
