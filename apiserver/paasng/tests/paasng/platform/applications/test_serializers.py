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
from rest_framework import serializers

from paasng.platform.applications.exceptions import AppFieldValidationError
from paasng.platform.applications.serializers import AppIDField, AppIDSMartField, AppNameField
from paasng.platform.applications.signals import prepare_use_application_code, prepare_use_application_name
from paasng.utils.i18n.serializers import I18NExtend, i18n
from tests.utils.basic import generate_random_string
from tests.utils.helpers import create_app

pytestmark = pytest.mark.django_db


class AppCodeSLZ(serializers.Serializer):
    code = AppIDField()


class TestAppIDField:
    def test_create_normal(self, random_name):
        slz = AppCodeSLZ(data={"code": random_name})
        assert slz.is_valid() is True

    def test_forbid_underscore(self):
        slz = AppCodeSLZ(data={"code": "foo_bar"})
        assert slz.is_valid() is False

    def test_create_existed_found(self, bk_app):
        slz = AppCodeSLZ(data={"code": bk_app.code})
        assert slz.is_valid() is False

    def test_create_existed_found_in_external(self, random_name):
        slz = AppCodeSLZ(data={"code": random_name})
        with mock.patch.object(prepare_use_application_code, "send") as mocked_send:
            mocked_send.side_effect = AppFieldValidationError("duplicated")
            assert slz.is_valid() is False

    def test_update_same_code(self, bk_app):
        slz = AppCodeSLZ(data={"code": bk_app.code}, instance=bk_app)
        assert slz.is_valid() is True

    def test_update_code_is_forbidden(self, bk_app):
        another_app = create_app()
        slz = AppCodeSLZ(data={"code": another_app.code}, instance=bk_app)
        assert slz.is_valid() is False

    def test_update_random_is_forbidden(self, bk_app, random_name):
        slz = AppCodeSLZ(data={"code": random_name}, instance=bk_app)
        assert slz.is_valid() is False


class AppIDSMartSLZ(serializers.Serializer):
    id = AppIDSMartField()


class TestAppIDSMartField:
    def test_max_length_is_20(self):
        slz = AppIDSMartSLZ(data={"id": "s" * 20})
        assert slz.is_valid() is True

        slz = AppIDSMartSLZ(data={"id": "s" * 21})
        assert slz.is_valid() is False

    def test_allow_underscore(self):
        slz = AppIDSMartSLZ(data={"id": "foo_bar"})
        assert slz.is_valid() is True


class AppNameSLZ(serializers.Serializer):
    name = AppNameField()


class TestAppNameField:
    def test_create_existed_found_in_external(self, random_name):
        slz = AppNameSLZ(data={"name": random_name}, context={"app_tenant_id": "default"})
        with mock.patch.object(prepare_use_application_name, "send") as mocked_send:
            mocked_send.side_effect = AppFieldValidationError("duplicated")
            assert slz.is_valid() is False

    def test_create_without_app_tenant_id_raises(self, random_name):
        """Creating without app_tenant_id should raise a validation error."""
        slz = AppNameSLZ(data={"name": random_name})
        assert slz.is_valid() is False

    def test_update_different_name(self, bk_app):
        slz = AppNameSLZ(data={"name": bk_app.name + "2"}, instance=bk_app)
        assert slz.is_valid() is True

    def test_update_existed_found_in_external(self, bk_app, random_name):
        slz = AppNameSLZ(data={"name": random_name}, instance=bk_app)
        with mock.patch.object(prepare_use_application_name, "send") as mocked_send:
            mocked_send.side_effect = AppFieldValidationError("duplicated")
            assert slz.is_valid() is False


class TestAppNameTenantUniqueness:
    """Tests that name uniqueness is scoped by ``app_tenant_id``.

    The validator narrows the queryset when it can resolve the tenant from
    ``instance`` (update) or serializer ``context``.
    """

    @pytest.fixture
    def random_tenant_id(self) -> str:
        return generate_random_string(12)

    def test_same_name_different_tenant_passes(self, bk_app, random_tenant_id):
        """Same name in a *different* tenant should pass."""
        bk_app.app_tenant_id = random_tenant_id
        bk_app.save(update_fields=["app_tenant_id"])

        slz = AppNameSLZ(data={"name": bk_app.name}, context={"app_tenant_id": random_tenant_id + "x"})
        assert slz.is_valid() is True

    def test_same_name_same_tenant_fails(self, bk_app, random_tenant_id):
        """Same name in the *same* tenant should fail."""
        bk_app.app_tenant_id = random_tenant_id
        bk_app.save(update_fields=["app_tenant_id"])

        slz = AppNameSLZ(data={"name": bk_app.name}, context={"app_tenant_id": random_tenant_id})
        assert slz.is_valid() is False
        assert "应用已存在" in str(slz.errors["name"])

    def test_no_tenant_info_raises(self, bk_app):
        """Without app_tenant_id, validation should fail with an error."""
        slz = AppNameSLZ(data={"name": bk_app.name})
        assert slz.is_valid() is False
        assert "app_tenant_id is required" in str(slz.errors["name"])

    def test_update_uses_instance_tenant(self, bk_app, random_name, random_tenant_id):
        """Update operation resolves tenant from the instance."""
        bk_app.app_tenant_id = random_tenant_id
        bk_app.save(update_fields=["app_tenant_id"])

        another_app = create_app()
        another_app.name = random_name
        another_app.app_tenant_id = random_tenant_id
        another_app.save(update_fields=["name", "app_tenant_id"])

        # Update bk_app to another_app's name — same tenant, should fail
        slz = AppNameSLZ(data={"name": another_app.name}, instance=bk_app)
        assert slz.is_valid() is False
        assert "应用已存在" in str(slz.errors["name"])


class AppDescSLZ(serializers.Serializer):
    """Mirrors AppDescriptionSLZ where AppNameField uses explicit ``source``."""

    bk_app_name = AppNameField(source="name_zh_cn")
    bk_app_name_en = AppNameField(source="name_en", required=False)


class TestAppNameFieldWithSource:
    """Tests for AppNameField with explicit ``source`` (e.g. declarative AppDescriptionSLZ).

    Validates that the validator resolves the model field from ``source``
    rather than using the hardcoded ``field_name = "name"``.
    """

    def test_name_en_duplicate_detected(self, bk_app, random_name):
        """bk_app_name_en with source='name_en' should check the name_en column."""
        slz = AppDescSLZ(
            data={"bk_app_name": random_name, "bk_app_name_en": bk_app.name_en},
            context={"app_tenant_id": bk_app.app_tenant_id},
        )
        assert slz.is_valid() is False
        assert "应用已存在" in str(slz.errors["bk_app_name_en"])

    def test_name_en_unique_passes(self, bk_app, random_name):
        slz = AppDescSLZ(
            data={"bk_app_name": random_name, "bk_app_name_en": bk_app.name_en + "x"},
            context={"app_tenant_id": bk_app.app_tenant_id},
        )
        assert slz.is_valid() is True

    def test_name_en_not_checked_against_name_column(self, bk_app, random_name):
        """Even if bk_app_name_en value matches another app's ``name``,
        it should pass when no app has the same ``name_en``."""
        another_app = create_app()
        another_app.name_en = random_name
        another_app.save(update_fields=["name_en"])

        slz = AppDescSLZ(
            data={"bk_app_name": random_name, "bk_app_name_en": another_app.name},
            context={"app_tenant_id": bk_app.app_tenant_id},
        )
        assert slz.is_valid() is True


@i18n
class I18NAppNameSLZ(serializers.Serializer):
    """Serializer that mirrors the real usage: I18NExtend(AppNameField())"""

    name = I18NExtend(AppNameField())


class TestAppNameFieldI18N:
    """Tests for AppNameField used through I18NExtend / @i18n decorator."""

    def test_name_duplicate_detected(self, bk_app, random_name):
        """name value matching existing name should fail."""
        duplicate_cases = [
            {"name": bk_app.name},
            {"name_zh_cn": random_name, "name_en": bk_app.name_en},
            {"name_zh_cn": bk_app.name, "name_en": random_name},
        ]
        for data in duplicate_cases:
            slz = I18NAppNameSLZ(data=data, context={"app_tenant_id": bk_app.app_tenant_id})
            assert slz.is_valid() is False
            assert "应用已存在" in str(slz.errors["name"])

    def test_name_unique_passes(self, bk_app, random_name):
        """name value not matching any existing name should pass."""
        unique_cases = [
            {"name": random_name},
            {"name_zh_cn": random_name, "name_en": random_name},
        ]
        for data in unique_cases:
            slz = I18NAppNameSLZ(data=data, context={"app_tenant_id": bk_app.app_tenant_id})
            assert slz.is_valid() is True

    def test_name_en_not_checked_against_name_column(self, bk_app, random_name):
        """name_en uniqueness must NOT be checked against the ``name`` column.

        Even if name_en equals another app's ``name``, it should pass as long
        as no other app has the same ``name_en``.
        """
        another_app = create_app()
        # Set name_en to something unique to avoid collision
        another_app.name_en = random_name
        another_app.save(update_fields=["name_en"])

        # Use another_app.name as the name_en value — should pass because
        # uniqueness of name_en is checked on the name_en column, not name.
        slz = I18NAppNameSLZ(
            data={"name_zh_cn": random_name, "name_en": another_app.name},
            context={"app_tenant_id": bk_app.app_tenant_id},
        )
        assert slz.is_valid() is True

    def test_update_same_name_en(self, bk_app):
        """Updating with the same name_en should pass (exclude self)."""
        slz = I18NAppNameSLZ(
            data={"name_zh_cn": bk_app.name, "name_en": bk_app.name_en},
            instance=bk_app,
        )
        assert slz.is_valid() is True
