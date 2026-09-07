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
from rest_framework.exceptions import ValidationError

from paas_wl.bk_app.processes.models import ProcessSpecPlan
from paasng.platform.bkapp_model.models import ResQuotaPlan
from paasng.platform.bkapp_model.res_quota import PLAN_UNAVAILABLE, ResQuotaPlanPolicy
from paasng.platform.declarative.utils import get_quota_plan

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _create_plan(name, allowed_app_codes=None, is_active=True):
    return ResQuotaPlan.objects.create(
        name=name,
        limits={"cpu": "2000m", "memory": "4096Mi"},
        requests={"cpu": "2000m", "memory": "4096Mi"},
        is_active=is_active,
        allowed_app_codes=allowed_app_codes or [],
    )


class TestResQuotaPlanPolicy:
    def test_normalize_allowed_app_codes(self):
        policy = ResQuotaPlanPolicy()
        assert policy.normalize_allowed_app_codes([" bk-hids ", "", "bk-hids", None, "future-app"]) == [
            "bk-hids",
            "future-app",
        ]
        assert policy.normalize_allowed_app_codes([]) == []
        assert policy.normalize_allowed_app_codes(None) == []

    def test_can_select(self):
        policy = ResQuotaPlanPolicy()
        public = _create_plan("public-plan")
        dedicated = _create_plan("dedicated-plan", allowed_app_codes=["bk-hids"])
        inactive = _create_plan("inactive-plan", allowed_app_codes=["bk-hids"], is_active=False)

        assert policy.can_select(public, "anyone")
        assert policy.can_select(public, None)
        assert policy.can_select(dedicated, "bk-hids")
        assert not policy.can_select(dedicated, "other-app")
        assert not policy.can_select(dedicated, None)
        assert not policy.can_select(inactive, "bk-hids")

    def test_can_assign_retain_and_new_select(self):
        policy = ResQuotaPlanPolicy()
        dedicated = _create_plan("dedicated-plan", allowed_app_codes=["bk-hids"])

        assert policy.can_assign(dedicated.name, "bk-hids")
        assert not policy.can_assign(dedicated.name, "other-app")
        assert policy.can_assign(dedicated.name, "other-app", current_plan_name=dedicated.name)
        assert not policy.can_assign("missing-plan", "bk-hids")

    def test_ensure_assignable_message_does_not_leak_whitelist(self):
        policy = ResQuotaPlanPolicy()
        _create_plan("dedicated-plan", allowed_app_codes=["secret-app"])
        with pytest.raises(ValidationError) as exc:
            policy.ensure_assignable("dedicated-plan", "other-app")
        assert str(PLAN_UNAVAILABLE) in str(exc.value)
        assert "secret-app" not in str(exc.value)


class TestGetQuotaPlan:
    def test_existing_public_plan(self):
        _create_plan("public-plan")
        assert get_quota_plan("public-plan", app_code="any-app") == "public-plan"

    def test_existing_dedicated_plan_unauthorized_does_not_fallback(self):
        _create_plan("dedicated-plan", allowed_app_codes=["bk-hids"])
        with pytest.raises(ValidationError) as exc:
            get_quota_plan("dedicated-plan", app_code="other-app")
        assert "secret" not in str(exc.value)
        assert "bk-hids" not in str(exc.value)

    def test_existing_dedicated_plan_retain(self):
        _create_plan("dedicated-plan", allowed_app_codes=["bk-hids"])
        assert get_quota_plan("dedicated-plan", app_code="other-app", current_plan_name="dedicated-plan") == (
            "dedicated-plan"
        )

    def test_unknown_name_still_falls_back_to_default(self):
        assert get_quota_plan("non-existent-plan") == "default"

    def test_unknown_legacy_process_spec_plan(self):
        ProcessSpecPlan.objects.get_or_create(
            name="legacy-4c2g",
            defaults={
                "max_replicas": 5,
                "limits": {"memory": "2048Mi", "cpu": "4000m"},
                "requests": {"memory": "1024Mi", "cpu": "200m"},
            },
        )
        assert get_quota_plan("legacy-4c2g") == "legacy-4c2g"
