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
from django.utils.translation import gettext_lazy as _

from paasng.bk_plugins.pluginscenter.constants import ActionTypes, PluginReleaseStatus, SubjectTypes
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.models import OperationRecord, PluginRelease
from tests.paasng.bk_plugins.pluginscenter.conftest import make_api_resource

pytestmark = pytest.mark.django_db


class TestReleaseStages:
    """Release 状态扭转的集成测试"""

    @pytest.fixture(autouse=True)
    def _mock_refresh_source_hash(self):
        with mock.patch("paasng.bk_plugins.pluginscenter.releases.stages.DeployAPIStage._refresh_source_hash"):
            yield

    @pytest.fixture()
    def _setup_release_stages(self, pd):
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
        pd.test_release_stages = [
            {
                "id": "market",
                "name": "完善市场信息",
                "invokeMethod": "builtin",
            }
        ]
        pd.save()
        pd.refresh_from_db()

    @pytest.mark.parametrize(
        ("release_type", "source_version_name", "version", "status_code", "resp_code"),
        [  # 当前插件有未完成的测试版本,仍可创建新分支测试版本
            ("test", "testbranch1", "testbranch1-2501191602", 201, ""),
            # 测试版本设置了：不允许选择正在发布过的代码分支
            ("test", "testbranch", "testbranch-2501191602", 400, "CANNOT_RELEASE_RELEASING_SOURCE_VERSION"),
            # 当前插件有未完成的正式版本,不能创建正式版本
            ("prod", "foo", "0.0.2", 400, "CANNOT_RELEASE_ONGOING_EXISTS"),
        ],
    )
    @pytest.mark.usefixtures("_setup_release_stages", "_setup_bk_user")
    def test_create_release_version(
        self,
        test_release,
        release,
        pd,
        plugin,
        api_client,
        iam_policy_client,
        release_type,
        source_version_name,
        version,
        status_code,
        resp_code,
    ):
        # 当前插件有未完成的测试版本,仍可创建测试版本
        assert (
            PluginRelease.objects.filter(
                plugin=plugin, type=release_type, status__in=PluginReleaseStatus.running_status()
            ).count()
            == 1
        )
        with mock.patch("paasng.bk_plugins.pluginscenter.views.get_plugin_repo_accessor") as get_plugin_repo_accessor:
            get_plugin_repo_accessor().extract_smart_revision.return_value = "hash"
            # 创建测试版本发布
            resp = api_client.post(
                f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/",
                data={
                    "type": release_type,
                    "source_version_type": "branch",
                    "source_version_name": source_version_name,
                    "version": version,
                    "comment": "...",
                    "semver_type": "patch",
                },
            )
            assert resp.status_code == status_code
            if status_code != 201:
                assert resp.json()["code"] == resp_code

    @pytest.mark.usefixtures("_setup_release_stages", "_setup_bk_user")
    def test_release_version(self, thirdparty_client, pd, plugin, api_client, iam_policy_client):
        # 当前插件没有正在执行的正式版本，可创建新的正式版本
        assert (
            PluginRelease.objects.filter(
                plugin=plugin, type="prod", status__in=PluginReleaseStatus.running_status()
            ).count()
            == 0
        )
        with mock.patch("paasng.bk_plugins.pluginscenter.views.get_plugin_repo_accessor") as get_plugin_repo_accessor:
            get_plugin_repo_accessor().extract_smart_revision.return_value = "hash"
            # 创建正式版本发布
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
            "code": error_codes.EXECUTE_STAGE_ERROR.code,
            "detail": error_codes.EXECUTE_STAGE_ERROR.f(_("当前阶段未执行成功, 不允许进入下一阶段")).message,
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

        thirdparty_client.call.side_effect = deploy_action_side_effect

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
            "stage_id": "deploy",
            "stage_name": "部署",
            "status": "pending",
            "fail_message": "",
            "invoke_method": "deployAPI",
            "status_polling_method": "api",
            "detail": {
                "steps": [{"id": "step-1", "name": "步骤1", "status": "successful"}],
                "finished": True,
                "logs": ["1", "2", "3"],
            },
        }

        # 测试进入下一步(完成发布)
        # - 渲染 stage 时隐含了更新 status 的操作(后面需要重构成后台任务轮训更新状态)
        release.refresh_from_db()
        assert release.current_stage.status == PluginReleaseStatus.SUCCESSFUL
        # 最后一个步骤成功, 自动部署成功
        assert release.status == PluginReleaseStatus.SUCCESSFUL
        # release 已经成功完成后，再更新 stage 的信息时，不会再触发 release 状态的更新
        release.current_stage.status = PluginReleaseStatus.FAILED
        release.current_stage.operator = "xxxxxx"
        release.current_stage.save(update_fields=["status", "operator"])
        assert release.status == PluginReleaseStatus.SUCCESSFUL


class TestOperationRecord:
    """测试操作记录"""

    def test_record(self, plugin, bk_user):
        record = OperationRecord.objects.create(
            plugin=plugin,
            operator=bk_user.pk,
            action=ActionTypes.DELETE,
            subject=SubjectTypes.PLUGIN,
        )
        assert record.get_display_text() == f"{bk_user.username} 删除插件"

        record1 = OperationRecord.objects.create(
            plugin=plugin,
            operator=bk_user.pk,
            action=ActionTypes.ADD,
            specific="0.0.1",
            subject=SubjectTypes.VERSION,
        )
        assert record1.get_display_text() == f"{bk_user.username} 新建 0.0.1 版本"
