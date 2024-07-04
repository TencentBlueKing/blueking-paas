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

from paasng.platform.applications.protections import (
    AppResProtector,
    BaseAppResProtectCondition,
    ConditionNotMatched,
    ProtectedRes,
    ProtectionStatus,
)

pytestmark = pytest.mark.django_db


class ForbidUpdate(BaseAppResProtectCondition):
    def validate(self):
        raise ConditionNotMatched("forbidden", "forbidden")


class TestAppResProtector:
    def test_get_status_empty(self, bk_app):
        assert AppResProtector(bk_app).list_status() == {
            ProtectedRes.BASIC_INFO_MODIFICATIONS: ProtectionStatus([]),
            ProtectedRes.SERVICES_MODIFICATIONS: ProtectionStatus([]),
            ProtectedRes.DISABLE_APP_DESC: ProtectionStatus([]),
        }

    def test_smart_app(self, bk_app):
        bk_app.is_smart_app = True
        bk_app.save()
        assert AppResProtector(bk_app).list_status() == {
            ProtectedRes.BASIC_INFO_MODIFICATIONS: ProtectionStatus([]),
            ProtectedRes.SERVICES_MODIFICATIONS: ProtectionStatus([]),
            ProtectedRes.DISABLE_APP_DESC: ProtectionStatus(
                [ConditionNotMatched("S-Mart 不可关闭应用描述文件", "disable_application_description")]
            ),
        }

    def test_list_status(self, bk_app):
        with AppResProtector.override_preconditions(
            {ProtectedRes.BASIC_INFO_MODIFICATIONS: [ForbidUpdate], ProtectedRes.SERVICES_MODIFICATIONS: []}
        ):
            assert AppResProtector(bk_app).list_status() == {
                ProtectedRes.BASIC_INFO_MODIFICATIONS: ProtectionStatus(
                    [ConditionNotMatched("forbidden", "forbidden")]
                ),
                ProtectedRes.SERVICES_MODIFICATIONS: ProtectionStatus([]),
                ProtectedRes.DISABLE_APP_DESC: ProtectionStatus([]),
            }

    def test_get_status(self, bk_app):
        with AppResProtector.override_preconditions({ProtectedRes.BASIC_INFO_MODIFICATIONS: [ForbidUpdate]}):
            assert AppResProtector(bk_app).get_status(ProtectedRes.BASIC_INFO_MODIFICATIONS) == ProtectionStatus(
                [ConditionNotMatched("forbidden", "forbidden")]
            )
