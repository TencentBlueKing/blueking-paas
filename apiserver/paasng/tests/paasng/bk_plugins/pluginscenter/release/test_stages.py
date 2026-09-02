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
from blue_krill.web.std_error import APIError
from django_dynamic_fixture import G

from paasng.bk_plugins.pluginscenter.constants import PluginReleaseStatus, ReleaseStageInvokeMethod
from paasng.bk_plugins.pluginscenter.definitions import find_stage_by_id
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.models import PluginRelease, PluginReleaseStrategy
from paasng.bk_plugins.pluginscenter.models.instances import ItsmDetail
from paasng.bk_plugins.pluginscenter.releases.stages import (
    BaseStageController,
    CanaryWithItsmStage,
    PipelineStage,
    init_stage_controller,
)

pytestmark = pytest.mark.django_db


class TestPipelineStage:
    @pytest.fixture(autouse=True)
    def _setup(self, plugin, release):
        plugin.repository = "http://git.example.com/foo.git"
        plugin.save()
        release.source_location = plugin.repository
        release.source_version_type = "tag"
        release.source_version_name = "v1.0.0"
        release.save()

    @pytest.mark.parametrize(
        ("template", "expected"),
        [
            (
                {"repo_url": "{{ source_location }}", "tag": "{{ source_version_name }}"},
                {"repo_url": "http://git.example.com/foo.git", "tag": "v1.0.0"},
            ),
            (
                {"plugin_id": "{ source_location }"},
                {"plugin_id": "{ source_location }"},
            ),
        ],
    )
    def test_build_pipeline_params(self, pd, release, template, expected):
        # setup_release_stages
        pd.release_stages = [
            {
                "id": "pipeline",
                "name": "流水线构建",
                "invokeMethod": ReleaseStageInvokeMethod.PIPELINE,
                "pipelineId": 1,
                "pipelineParams": template,
            },
        ]
        pd.save()
        pd.refresh_from_db()
        release.refresh_from_db()
        release.initial_stage_set(force_refresh=True)

        current_stage = release.current_stage
        assert current_stage.stage_id == "pipeline"

        stage_ctl = PipelineStage(current_stage)
        stage_definition = find_stage_by_id(pd, release, current_stage.stage_id)  # type: ignore
        assert stage_definition
        assert stage_ctl.build_pipeline_params(stage_definition) == expected


class TestCanaryWithItsmStage:
    @pytest.fixture()
    def gray_release(self, pd, plugin) -> PluginRelease:
        """灰度发布阶段：invoke_method 为 canaryWithItsm。"""
        pd.release_stages = [
            {
                "id": "gray",
                "name": "带审批的灰度发布",
                "invokeMethod": ReleaseStageInvokeMethod.CANARY_WITH_ITSM,
            },
        ]
        pd.save()
        pd.refresh_from_db()

        release: PluginRelease = G(
            PluginRelease,
            plugin=plugin,
            source_location=plugin.repository,
            type="prod",
            source_version_type="branch",
            source_version_name="master",
            version="0.0.2",
            comment="",
        )
        release.initial_stage_set(force_refresh=True)
        return release

    @pytest.fixture()
    def stage(self, gray_release):
        return gray_release.all_stages.get(stage_id="gray")

    def test_get_stage_class(self):
        assert BaseStageController.get_stage_class(ReleaseStageInvokeMethod.CANARY_WITH_ITSM) is CanaryWithItsmStage
        assert BaseStageController.get_stage_class("canaryWithItsm") is CanaryWithItsmStage

    def test_init_stage_controller(self, stage):
        controller = init_stage_controller(stage)
        assert isinstance(controller, CanaryWithItsmStage)

    def test_render_to_view_without_ticket(self, stage):
        stage_info = CanaryWithItsmStage(stage).render_to_view()
        assert stage_info["stage_id"] == "gray"
        assert stage_info["invoke_method"] == ReleaseStageInvokeMethod.CANARY_WITH_ITSM
        assert stage_info["detail"] == {}

    def test_render_to_view_with_ticket(self, stage, gray_release):
        PluginReleaseStrategy.objects.create(
            release=gray_release,
            strategy="gray",
            itsm_detail=ItsmDetail(
                sn="sn-gray-1",
                fields=[{"key": "title", "value": "灰度发布审批"}],
                ticket_url="https://itsm.example.com/ticket/1",
            ),
        )
        ticket_status = {
            "ticket_url": "https://itsm.example.com/ticket/1",
            "current_status": "RUNNING",
            "current_status_display": "处理中",
            "can_withdraw": True,
        }
        with mock.patch(
            "paasng.bk_plugins.pluginscenter.releases.stages.get_ticket_status",
            return_value=ticket_status,
        ):
            stage_info = CanaryWithItsmStage(stage).render_to_view()

        assert stage_info["detail"]["ticket_url"] == "https://itsm.example.com/ticket/1"
        assert stage_info["detail"]["can_withdraw"] is True
        assert stage_info["detail"]["fields"] == [{"key": "title", "value": "灰度发布审批"}]
        assert stage_info["detail"]["sn"] == "sn-gray-1"

    def test_execute_raises(self, stage):
        with pytest.raises(APIError) as exc:
            CanaryWithItsmStage(stage).execute("admin")
        assert exc.value.code == error_codes.EXECUTE_STAGE_ERROR.code
        stage.refresh_from_db()
        assert stage.status == PluginReleaseStatus.INITIAL
