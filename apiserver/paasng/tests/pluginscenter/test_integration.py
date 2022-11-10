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
from unittest import mock

import pytest
from django.utils.translation import gettext_lazy as _

from paasng.pluginscenter.constants import PluginReleaseStatus
from paasng.pluginscenter.exceptions import error_codes
from paasng.pluginscenter.models import PluginRelease
from tests.pluginscenter.conftest import make_api_resource

pytestmark = pytest.mark.django_db


class TestReleaseStages:
    """Release 状态扭转的集成测试"""

    @pytest.fixture
    def setup_release_stages(self, pd):
        pd.release_stages = [
            {
                "id": "market",
                "name": "完善市场信息",
                "invokeMethod": "builtin",
            },
            {
                "id": "deploy",
                "name": "部署",
                "invokeMethod": "deployAPI",
                "api": {
                    "release": make_api_resource("/{plugin_id}/deploy/"),
                    "result": make_api_resource("/{plugin_id}/status/"),
                    "log": make_api_resource("/{plugin_id}/log/"),
                },
            },
        ]
        pd.save()
        pd.refresh_from_db()

    @pytest.fixture
    def disable_permission_check(self):
        with mock.patch("paasng.pluginscenter.iam_adaptor.policy.permissions.lazy_iam_client") as iam_policy_client:
            iam_policy_client.is_action_allowed.return_value = True
            iam_policy_client.is_actions_allowed.return_value = {"": True}
            yield

    def test_release_version(
        self, mock_client, pd, plugin, setup_release_stages, api_client, disable_permission_check
    ):
        assert PluginRelease.objects.count() == 0
        with mock.patch("paasng.pluginscenter.views.get_plugin_repo_accessor") as get_plugin_repo_accessor:
            get_plugin_repo_accessor().extract_smart_revision.return_value = "hash"
            # 测试创建版本发布
            resp = api_client.post(
                f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/",
                data={
                    "type": "prod",
                    "source_version_type": "branch",
                    "source_version_name": "foo",
                    "version": "0.0.1",
                    "comment": "...",
                    "semver_type": "patch",
                },
            )
            assert resp.status_code == 201

        release = PluginRelease.objects.get(plugin=plugin)
        assert release.current_stage.stage_id == "market"
        assert release.current_stage.status == PluginReleaseStatus.PENDING

        # 测试进入下一步(失败)
        resp = api_client.post(f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/{release.id}/next/")
        assert resp.status_code == 400
        assert resp.json() == {
            'code': error_codes.EXECUTE_STAGE_ERROR.code,
            'detail': error_codes.EXECUTE_STAGE_ERROR.f(_("当前阶段未执行成功, 不允许进入下一阶段")).message,
        }

        # 测试保存市场信息(完成当前阶段的操作)
        resp = api_client.post(
            f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/market/",
            data={"category": "...", "introduction": "...", "description": "...", "contact": "..."},
        )
        assert resp.status_code == 200
        release.refresh_from_db()
        assert release.current_stage.status == PluginReleaseStatus.SUCCESSFUL

        counter = 0

        def deploy_action_side_effect(*args, **kwargs):
            nonlocal counter
            counter += 1
            if counter == 1:
                return {
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
            elif counter == 2:
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

        # 再次测试进入下一步(成功)
        resp = api_client.post(f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/{release.id}/next/")
        assert resp.status_code == 200
        release.refresh_from_db()
        release.current_stage.refresh_from_db()
        assert release.current_stage.stage_id == "deploy"
        assert release.current_stage.api_detail == {
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

        # 测试前端渲染 stage 的状态
        resp = api_client.get(
            f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/{release.id}"
            f"/stages/{release.current_stage.stage_id}/"
        )
        assert resp.json() == {
            'stage_id': 'deploy',
            'stage_name': '部署',
            'status': 'pending',
            'fail_message': '',
            'detail': {
                'steps': [{'id': 'step-1', 'name': '步骤1', 'status': 'pending'}],
                'finished': True,
                'logs': ['1', '2', '3'],
            },
        }

        # 测试进入下一步(完成发布)
        # - 渲染 stage 时隐含了更新 status 的操作(后面需要重构成后台任务轮训更新状态)
        release.refresh_from_db()
        assert release.current_stage.status == PluginReleaseStatus.SUCCESSFUL
        assert release.status == PluginReleaseStatus.PENDING
        resp = api_client.post(f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/{release.id}/next/")
        assert resp.status_code == 200

        release.refresh_from_db()
        assert release.status == PluginReleaseStatus.SUCCESSFUL
