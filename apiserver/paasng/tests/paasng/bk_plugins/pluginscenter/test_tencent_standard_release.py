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

from unittest import mock

import pytest

from paasng.bk_plugins.pluginscenter.constants import GrayReleaseStatus, ReleaseProcess, ReleaseStrategy
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ApprovalServiceName
from paasng.bk_plugins.pluginscenter.models.instances import ItsmDetail
from paasng.bk_plugins.pluginscenter.thirdparty.api_serializers import PluginStrategySLZ
from paasng.bk_plugins.pluginscenter.views import _validate_release_strategy_step

pytestmark = pytest.mark.django_db


class TestTencentStandardReleaseProcess:
    def test_gray_uses_platform_admin_approval(self, release_strategy):
        release = release_strategy.release
        release.release_process = ReleaseProcess.TENCENT_STANDARD
        release.save(update_fields=["release_process"])
        release_strategy.organization = [{"id": 3, "type": "department", "name": "dept"}]
        release_strategy.save()

        assert release_strategy.get_itsm_service_name(is_organization_changed=True) == (
            ApprovalServiceName.CODECC_FULL_RELEASE_APPROVAL
        )

    def test_pre_prod_uses_platform_admin_approval(self, release_strategy):
        release = release_strategy.release
        release.release_process = ReleaseProcess.TENCENT_STANDARD
        release.save(update_fields=["release_process"])
        release_strategy.strategy = ReleaseStrategy.PRE_PROD
        release_strategy.save()

        assert release_strategy.get_itsm_service_name(is_organization_changed=False) == (
            ApprovalServiceName.CODECC_FULL_RELEASE_APPROVAL
        )

    def test_default_org_gray_still_uses_leader_approval(self, release_strategy):
        release_strategy.organization = [{"id": 3, "type": "department", "name": "dept"}]
        release_strategy.save()

        assert release_strategy.get_itsm_service_name(is_organization_changed=True) == (
            ApprovalServiceName.CODECC_ORG_GRAY_RELEASE_APPROVAL
        )

    def test_plugin_strategy_slz_adds_type_for_pre_prod(self, release_strategy):
        release_strategy.strategy = ReleaseStrategy.PRE_PROD
        release_strategy.save()

        data = PluginStrategySLZ(release_strategy).data
        assert data["strategy"] == "pre_prod"
        assert data["type"] == 4

    def test_plugin_strategy_slz_omits_type_for_gray(self, release_strategy):
        data = PluginStrategySLZ(release_strategy).data
        assert data["strategy"] == "gray"
        assert "type" not in data

    def test_cannot_apply_pre_prod_twice(self, release_strategy):
        release = release_strategy.release
        release.release_process = ReleaseProcess.TENCENT_STANDARD
        release.gray_status = GrayReleaseStatus.IN_GRAY
        release.save(update_fields=["release_process", "gray_status"])
        release_strategy.strategy = ReleaseStrategy.PRE_PROD
        release_strategy.save()

        from blue_krill.web.std_error import APIError

        with pytest.raises(APIError):
            _validate_release_strategy_step(release, ReleaseStrategy.PRE_PROD)

    def test_cannot_apply_full_before_pre_prod(self, release_strategy):
        release = release_strategy.release
        release.release_process = ReleaseProcess.TENCENT_STANDARD
        release.gray_status = GrayReleaseStatus.IN_GRAY
        release.save(update_fields=["release_process", "gray_status"])

        from blue_krill.web.std_error import APIError

        with pytest.raises(APIError):
            _validate_release_strategy_step(release, ReleaseStrategy.FULL)

    def test_can_apply_full_after_pre_prod(self, release_strategy):
        release = release_strategy.release
        release.release_process = ReleaseProcess.TENCENT_STANDARD
        release.gray_status = GrayReleaseStatus.IN_PRE_PROD
        release.save(update_fields=["release_process", "gray_status"])

        _validate_release_strategy_step(release, ReleaseStrategy.FULL)

    @pytest.mark.usefixtures("_enable_plugin_center")
    def test_update_pre_prod_strategy(
        self,
        api_client,
        pd,
        plugin,
        release_strategy,
        iam_policy_client,
        full_release_approval_service,
    ):
        release = release_strategy.release
        release.release_process = ReleaseProcess.TENCENT_STANDARD
        release.gray_status = GrayReleaseStatus.IN_GRAY
        release.status = "pending"
        release.save()
        release_strategy.itsm_detail = ItsmDetail(fields=[], sn="222", ticket_url="http://222")
        release_strategy.save()

        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/{release.id}/strategy/"
        with (
            mock.patch(
                "paasng.bk_plugins.pluginscenter.itsm_adaptor.client.ItsmClient.create_ticket",
                return_value=ItsmDetail(fields=[], sn="3333", ticket_url="http://3333"),
            ),
            mock.patch(
                "paasng.bk_plugins.pluginscenter.itsm_adaptor.client.ItsmClient.get_ticket_status",
                return_value={"ticket_url": "https://xxxx", "current_status": "FINISHED"},
            ),
            mock.patch(
                "paasng.bk_plugins.pluginscenter.iam_adaptor.management.shim.fetch_role_members",
                return_value=["admin"],
            ),
        ):
            resp = api_client.post(url, data={"strategy": "pre_prod"})

        assert resp.status_code == 200
        assert resp.json()["strategy"] == "pre_prod"
        release.refresh_from_db()
        assert release.gray_status == GrayReleaseStatus.PRE_PROD_APPROVAL_IN_PROGRESS
