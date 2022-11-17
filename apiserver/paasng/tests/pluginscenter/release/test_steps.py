"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import pytest

from paasng.pluginscenter.constants import PluginReleaseStatus, ReleaseStageInvokeMethod
from paasng.pluginscenter.models import PluginRelease
from paasng.pluginscenter.releases import stages
from tests.pluginscenter.conftest import make_api_resource

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_release_stages(pd):
    pd.release_stages = [
        {
            "id": "market",
            "name": "完善市场信息",
            "invokeMethod": ReleaseStageInvokeMethod.BUILTIN,
        },
        {
            "id": "deploy",
            "name": "部署",
            "invokeMethod": ReleaseStageInvokeMethod.DEPLOY_API,
            "api": {
                "release": make_api_resource("/{plugin_id}/deploy/"),
                "result": make_api_resource("/{plugin_id}/status/"),
                "log": make_api_resource("/{plugin_id}/log/"),
            },
        },
        {"id": "itsm", "name": "审批流程", "invokeMethod": ReleaseStageInvokeMethod.ITSM, "itsmServiceName": "foo"},
    ]
    pd.save()
    pd.refresh_from_db()


@pytest.fixture
def release(setup_release_stages, release) -> PluginRelease:
    release.initial_stage_set(force_refresh=True)
    return release


def test_stage_types():
    assert stages.BaseStageController._stage_types is stages.DeployAPIStage._stage_types


def test_render_base_info(release):
    for stage, expected in zip(release.all_stages.all(), [{}]):
        base_info = stages.BaseStageController(stage).render_to_view()
        assert base_info["stage_id"] == stage.stage_id
        assert base_info["stage_name"] == stage.stage_name
        assert base_info["status"] == PluginReleaseStatus.INITIAL
        assert base_info["fail_message"] == ''


class TestDeployAPIStage:
    @pytest.fixture
    def stage(self, release):
        stage = release.all_stages.get(stage_id="deploy")
        release.current_stage = stage
        release.save()
        return stage

    @pytest.fixture
    def stage_executor(self, stage):
        return stages.DeployAPIStage(stage)

    def test_execute(self, mock_client, stage, stage_executor):
        mock_client.call.return_value = {
            "deploy_id": "...",
            "status": "pending",
            "detail": "",
            "steps": [
                {
                    "id": "step-1",
                    "name": "步骤1",
                    "status": "pending",
                }
            ],
        }
        stage_executor.execute("")
        stage.refresh_from_db()
        assert stage.status == PluginReleaseStatus.PENDING
        assert stage.api_detail == {
            "deploy_id": "...",
            "status": "pending",
            "detail": "",
            "steps": [
                {
                    "id": "step-1",
                    "name": "步骤1",
                    "status": "pending",
                }
            ],
        }

    def test_render_to_view(self, mock_client, stage, stage_executor):
        stage.api_detail = {"deploy_id": "..."}
        stage.status = PluginReleaseStatus.PENDING
        stage.save()

        counter = 0
        def deploy_action_side_effect(*args, **kwargs):
            nonlocal counter
            counter += 1
            if counter == 1:
                return {
                    "deploy_id": "...",
                    "status": "successful",
                    "detail": "",
                    "steps": [
                        {
                            "id": "step-1",
                            "name": "步骤1",
                            "status": "successful",
                        }
                    ],
                }
            else:
                return {"logs": ["1", "2", "3"], "finished": True}

        mock_client.call.side_effect = deploy_action_side_effect
        stage_info = stage_executor.render_to_view()

        assert stage_info["detail"]["steps"] == [
            {
                "id": "step-1",
                "name": "步骤1",
                "status": "successful",
            }
        ]
        assert stage_info["detail"]["finished"] is True
        assert stage_info["detail"]["logs"] == ["1", "2", "3"]
