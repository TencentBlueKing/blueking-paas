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
from rest_framework import serializers

from paasng.platform.applications.exceptions import AppFieldValidationError
from paasng.platform.applications.serializers import AppIDField, AppNameField
from paasng.platform.applications.signals import prepare_use_application_code, prepare_use_application_name
from tests.utils.helpers import create_app

pytestmark = pytest.mark.django_db


class AppCodeSLZ(serializers.Serializer):
    code = AppIDField()


class TestAppIDField:
    def test_create_normal(self, random_name):
        slz = AppCodeSLZ(data={'code': random_name})
        assert slz.is_valid() is True

    def test_create_existed_found(self, bk_app):
        slz = AppCodeSLZ(data={'code': bk_app.code})
        assert slz.is_valid() is False

    def test_create_existed_found_in_external(self, random_name):
        slz = AppCodeSLZ(data={'code': random_name})
        with mock.patch.object(prepare_use_application_code, 'send') as mocked_send:
            mocked_send.side_effect = AppFieldValidationError('duplicated')
            assert slz.is_valid() is False

    def test_update_same_code(self, bk_app):
        slz = AppCodeSLZ(data={'code': bk_app.code}, instance=bk_app)
        assert slz.is_valid() is True

    def test_update_code_is_forbidden(self, bk_app):
        another_app = create_app()
        slz = AppCodeSLZ(data={'code': another_app.code}, instance=bk_app)
        assert slz.is_valid() is False

    def test_update_random_is_forbidden(self, bk_app, random_name):
        slz = AppCodeSLZ(data={'code': random_name}, instance=bk_app)
        assert slz.is_valid() is False


class AppNameSLZ(serializers.Serializer):
    name = AppNameField()


class TestAppNameField:
    def test_create_existed_found_in_external(self, random_name):
        slz = AppNameSLZ(data={'name': random_name})
        with mock.patch.object(prepare_use_application_name, 'send') as mocked_send:
            mocked_send.side_effect = AppFieldValidationError('duplicated')
            assert slz.is_valid() is False

    def test_update_different_name(self, bk_app):
        slz = AppNameSLZ(data={'name': bk_app.name + '2'}, instance=bk_app)
        assert slz.is_valid() is True

    def test_update_existed_found_in_external(self, bk_app, random_name):
        slz = AppNameSLZ(data={'name': random_name}, instance=bk_app)
        with mock.patch.object(prepare_use_application_name, 'send') as mocked_send:
            mocked_send.side_effect = AppFieldValidationError('duplicated')
            assert slz.is_valid() is False
