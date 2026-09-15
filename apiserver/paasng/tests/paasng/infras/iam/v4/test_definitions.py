# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from paasng.infras.iam.exceptions import InvalidIAMIdentifierError
from paasng.infras.iam.permissions.resources.application import AppRole
from paasng.infras.iam.v4.definitions import (
    ActionDefinition,
    RoleDefinition,
    SystemDefinition,
    build_paas_system_definition,
    is_valid_v4_identifier,
    validate_identifiers,
)


@pytest.fixture()
def iam_v4_settings(settings):
    settings.IAM_PAAS_V3_SYSTEM_ID = "bk_paas3"
    settings.IAM_APP_CODE = "bk_paas3"
    settings.BK_IAM_RESOURCE_API_HOST = "http://paas.example.com"


class TestLocalDefinitions:
    def test_paas_model_counts(self, iam_v4_settings):
        definition = build_paas_system_definition()

        assert definition.id == "bk_paas3"
        assert [item.id for item in definition.resource_types] == ["application"]
        assert len(definition.actions) == 14
        assert [role.id for role in definition.roles] == [str(role) for role in AppRole]
        assert [role.name for role in definition.roles] == [str(AppRole.get_choice_label(role)) for role in AppRole]
        assert "related_actions" not in definition.to_create_payload()

    def test_developer_actions_follow_code_not_template(self):
        assert len(AppRole.get_actions(AppRole.DEVELOPER)) == 8


class TestIdentifierValidation:
    @pytest.mark.parametrize("value", ["application", "view_basic_info", "app_administrator", "bk_paas3"])
    def test_accepts_valid_ids(self, value):
        assert is_valid_v4_identifier(value)

    @pytest.mark.parametrize("value", ["Application", "1abc", "has space", "too_long_identifier_over_32_chars_xx", ""])
    def test_rejects_invalid_ids(self, value):
        assert not is_valid_v4_identifier(value)

    def test_validate_lists_all_invalid_ids(self):
        definition = SystemDefinition(
            id="BadSystem",
            name="x",
            description="",
            clients=["c"],
            callback_url="http://example.com",
            resource_types=[],
            actions=[ActionDefinition(id="1bad", name="n", resource_type_id="application")],
            roles=[RoleDefinition(id="ok_role", name="r", description="")],
        )

        with pytest.raises(InvalidIAMIdentifierError) as exc_info:
            validate_identifiers([definition])

        assert exc_info.value.identifiers == ["BadSystem", "1bad"]
