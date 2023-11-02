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
import pytest

from paasng.bk_plugins.pluginscenter.constants import ReleaseStageInvokeMethod
from paasng.bk_plugins.pluginscenter.definitions import find_stage_by_id
from paasng.bk_plugins.pluginscenter.releases.stages import PipelineStage

pytestmark = pytest.mark.django_db


class TestPipelineStage:
    @pytest.fixture(autouse=True)
    def setup(self, plugin, release):
        plugin.repository = "http://git.example.com/foo.git"
        plugin.save()
        release.source_location = plugin.repository
        release.source_version_type = "tag"
        release.source_version_name = "v1.0.0"
        release.save()

    @pytest.mark.parametrize(
        "template, expected",
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
        stage_definition = find_stage_by_id(pd.release_stages, current_stage.stage_id)  # type: ignore
        assert stage_definition
        assert stage_ctl.build_pipeline_params(stage_definition) == expected
