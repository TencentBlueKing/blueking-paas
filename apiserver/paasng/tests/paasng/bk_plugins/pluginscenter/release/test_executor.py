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

import time
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import PollingMetadata, PollingResult, TaskPoller
from blue_krill.web.std_error import APIError
from django.utils.translation import gettext_lazy as _

from paasng.bk_plugins.pluginscenter.constants import PluginReleaseStatus, ReleaseStageInvokeMethod
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.models import PluginRelease, PluginReleaseStage
from paasng.bk_plugins.pluginscenter.releases.executor import PluginReleaseExecutor

pytestmark = pytest.mark.django_db


class FakeTaskPoller(TaskPoller):
    """A task poller for testing"""

    def query(self) -> PollingResult:
        stage_controller = build_stage_controller(
            self.params["target_status"], post_command_result=self.params["post_command_result"]
        )
        # 当前步骤执行结束后，执行后置命令
        is_success = stage_controller(self.params["stage"]).execute_post_command()
        if not is_success:
            self.params["stage"].update_status(PluginReleaseStatus.FAILED, "execute post command error")
            return PollingResult.done()

        return PollingResult.done()


def build_stage_controller(
    target_status: PluginReleaseStatus, pre_command_result: bool = True, post_command_result: bool = True
):
    class StageStatusSetter:
        def __init__(self, stage: PluginReleaseStage):
            self.release = stage.release
            self.plugin = self.release.plugin
            self.pd = self.plugin.pd
            self.stage = stage

        def execute(self, operator: str):
            self.stage.update_status(target_status)
            metadata = PollingMetadata(retries=0, query_started_at=time.time(), queried_count=0)
            params = {"stage": self.stage, "target_status": target_status, "post_command_result": post_command_result}
            FakeTaskPoller(params, metadata).query()

        def execute_pre_command(self, operator: str):
            return pre_command_result

        def execute_post_command(self):
            return post_command_result

    return StageStatusSetter


class TestPluginReleaseExecutor:
    @pytest.fixture()
    def _setup_release_stages(self, pd):
        pd.release_stages = [
            {
                "id": "stage1",
                "name": "stage1",
                "invokeMethod": ReleaseStageInvokeMethod.BUILTIN,
            },
            {
                "id": "stage2",
                "name": "stage2",
                "invokeMethod": ReleaseStageInvokeMethod.BUILTIN,
            },
            {
                "id": "stage3",
                "name": "stage3",
                "invokeMethod": ReleaseStageInvokeMethod.BUILTIN,
            },
            {
                "id": "stage4",
                "name": "stage4",
                "invokeMethod": ReleaseStageInvokeMethod.ITSM,
            },
        ]
        pd.save()
        pd.refresh_from_db()

    @pytest.fixture()
    def release(self, _setup_release_stages, release) -> PluginRelease:
        release.initial_stage_set(force_refresh=True)
        return release

    @pytest.fixture()
    def stage_class_setter(self):
        with mock.patch(
            "paasng.bk_plugins.pluginscenter.releases.stages.BaseStageController.get_stage_class"
        ) as mocked:
            yield mocked

    def test_enter_next_stage(self, release, stage_class_setter):
        executor = PluginReleaseExecutor(release)
        # 测试非成功阶段无法进入下一步
        assert release.current_stage.status == PluginReleaseStatus.INITIAL
        with pytest.raises(APIError) as exc:
            executor.enter_next_stage("")
        assert exc.value.code == error_codes.EXECUTE_STAGE_ERROR.code
        assert (
            exc.value.message == error_codes.EXECUTE_STAGE_ERROR.f(_("当前阶段未执行成功, 不允许进入下一阶段")).message
        )

        # 测试成功进入下一步, 同时下一步执行失败
        stage_class_setter.return_value = build_stage_controller(PluginReleaseStatus.INTERRUPTED)
        release.current_stage.status = PluginReleaseStatus.SUCCESSFUL
        release.current_stage.save()
        assert release.current_stage.stage_id == "stage1"
        executor.enter_next_stage("")
        release.refresh_from_db()
        assert release.current_stage.stage_id == "stage2"
        assert release.current_stage.status == PluginReleaseStatus.INTERRUPTED
        assert release.status == PluginReleaseStatus.INTERRUPTED

    def test_rerun_current_stage(self, release, stage_class_setter):
        executor = PluginReleaseExecutor(release)
        # 测试非失败的阶段无法 rerun
        assert release.current_stage.status == PluginReleaseStatus.INITIAL
        with pytest.raises(APIError) as exc:
            executor.rerun_current_stage("")
        assert exc.value.code == error_codes.CANNOT_RERUN_ONGOING_STEPS.code
        assert exc.value.message == error_codes.CANNOT_RERUN_ONGOING_STEPS.message

        # 测试失败阶段可以 rerun
        stage_class_setter.return_value = build_stage_controller(PluginReleaseStatus.SUCCESSFUL)
        release.current_stage.update_status(PluginReleaseStatus.FAILED)
        assert release.current_stage.stage_id == "stage1"
        executor.rerun_current_stage("")
        assert release.current_stage.stage_id == "stage1"
        assert release.current_stage.status == PluginReleaseStatus.SUCCESSFUL

    def test_execute_current_stage(self, release, stage_class_setter):
        executor = PluginReleaseExecutor(release)
        assert release.current_stage.status == PluginReleaseStatus.INITIAL
        assert release.current_stage.stage_id == "stage1"
        executor.execute_current_stage("")
        assert release.current_stage.stage_id == "stage1"
        assert release.current_stage.status == PluginReleaseStatus.PENDING

        # 已执行的步骤不能重试执行
        with pytest.raises(APIError) as exc:
            executor.execute_current_stage("")
        assert exc.value.code == error_codes.EXECUTE_STAGE_ERROR.code
        assert (
            exc.value.message
            == error_codes.EXECUTE_STAGE_ERROR.f(_("当前阶段已被执行, 不能重复触发已执行的阶段")).message
        )

        # 测试设置 status 为成功
        release.current_stage.reset()
        stage_class_setter.return_value = build_stage_controller(PluginReleaseStatus.SUCCESSFUL)
        assert release.current_stage.stage_id == "stage1"
        executor.execute_current_stage("")
        assert release.current_stage.stage_id == "stage1"
        assert release.current_stage.status == PluginReleaseStatus.SUCCESSFUL

    def test_rollback_current_stage_failed(self, release):
        executor = PluginReleaseExecutor(release)
        # 测试无上一步时不能返回上一步
        with pytest.raises(APIError) as exc:
            executor.back_to_previous_stage("")
        assert exc.value.code == error_codes.CANNOT_ROLLBACK_CURRENT_STEP.code
        assert exc.value.message == error_codes.CANNOT_ROLLBACK_CURRENT_STEP.message

        # 测试发布流程完成后不能返回上一步
        release.status = PluginReleaseStatus.SUCCESSFUL
        release.save()
        with pytest.raises(APIError) as exc:
            executor.back_to_previous_stage("")
        assert exc.value.code == error_codes.CANNOT_ROLLBACK_CURRENT_STEP.code
        assert exc.value.message == error_codes.CANNOT_ROLLBACK_CURRENT_STEP.f(_("当前发布流程已结束")).message

        # 测试 ITSM 流程未结束时不能返回上一步
        release.current_stage = release.all_stages.get(invoke_method=ReleaseStageInvokeMethod.ITSM)
        release.current_stage.update_status(PluginReleaseStatus.PENDING)
        release.status = PluginReleaseStatus.PENDING
        with pytest.raises(APIError) as exc:
            executor.back_to_previous_stage("")
        assert exc.value.code == error_codes.CANNOT_ROLLBACK_CURRENT_STEP.code
        assert (
            exc.value.message
            == error_codes.CANNOT_ROLLBACK_CURRENT_STEP.f(_("请先撤回审批单据, 再返回上一步")).message
        )

    def test_rollback_current_stage(self, release):
        executor = PluginReleaseExecutor(release)

        release.current_stage.update_status(PluginReleaseStatus.SUCCESSFUL)
        release.current_stage = release.current_stage.next_stage
        release.current_stage.update_status(PluginReleaseStatus.FAILED, "fail message")
        release.save()
        stage_pk = release.current_stage.pk

        assert release.current_stage.stage_id == "stage2"
        executor.back_to_previous_stage("")
        assert release.current_stage.stage_id == "stage1"
        assert release.current_stage.status == PluginReleaseStatus.SUCCESSFUL
        # 验证状态仅状态被重置
        assert release.current_stage.next_stage.pk == stage_pk
        assert release.current_stage.next_stage.status == PluginReleaseStatus.INITIAL
        assert release.current_stage.next_stage.fail_message == ""

    def test_reset(self, release):
        executor = PluginReleaseExecutor(release)
        # 测试非失败的阶段无法 reset
        with pytest.raises(APIError) as exc:
            executor.reset_release("")
        assert exc.value.code == error_codes.CANNOT_RESET_RELEASE.code
        assert (
            exc.value.message == error_codes.CANNOT_RESET_RELEASE.f(_("状态异常: {}").format(release.status)).message
        )

        release.all_stages.update(status=PluginReleaseStatus.SUCCESSFUL)
        release.current_stage = release.all_stages.get(stage_id="stage4")
        release.save()
        release.current_stage.update_status(status=PluginReleaseStatus.INTERRUPTED)

        # 验证阶段数据被重建
        assert release.current_stage.stage_id == "stage4"
        executor.reset_release("")
        assert release.current_stage.stage_id == "stage1"
        assert release.all_stages.get(stage_id="stage1").status == PluginReleaseStatus.PENDING
        assert release.all_stages.get(stage_id="stage2").status == PluginReleaseStatus.INITIAL
        assert release.all_stages.get(stage_id="stage3").status == PluginReleaseStatus.INITIAL
        assert release.all_stages.get(stage_id="stage4").status == PluginReleaseStatus.INITIAL

    def test_cancel(self, release):
        executor = PluginReleaseExecutor(release)
        # 测试取消成功
        executor.cancel_release("")
        release.refresh_from_db()
        assert release.status == PluginReleaseStatus.INTERRUPTED
        assert release.current_stage.status == PluginReleaseStatus.INTERRUPTED
        assert release.current_stage.fail_message == _("用户主动终止发布")

        # 测试发布流程完成后不能返回取消
        release.status = PluginReleaseStatus.SUCCESSFUL
        release.save()

        with pytest.raises(APIError) as exc:
            executor.cancel_release("")
        assert exc.value.code == error_codes.CANNOT_CANCEL_RELEASE.code

    @pytest.mark.parametrize(
        ("pre_command_result", "stage_status", "raise_exception"),
        [(True, PluginReleaseStatus.SUCCESSFUL, False), (False, PluginReleaseStatus.FAILED, True)],
    )
    def test_pre_command(self, release, stage_class_setter, pre_command_result, stage_status, raise_exception):
        executor = PluginReleaseExecutor(release)
        release.current_stage.reset()
        stage_class_setter.return_value = build_stage_controller(PluginReleaseStatus.SUCCESSFUL, pre_command_result)
        assert release.current_stage.stage_id == "stage1"
        if raise_exception:
            with pytest.raises(APIError) as exc:
                executor.execute_current_stage("")
            assert exc.value.code == error_codes.THIRD_PARTY_API_ERROR.code
        else:
            executor.execute_current_stage("")
            assert release.current_stage.stage_id == "stage1"
            assert release.current_stage.status == stage_status

    @pytest.mark.parametrize(
        ("post_command_result", "stage_status"),
        [
            (True, PluginReleaseStatus.SUCCESSFUL),
            (False, PluginReleaseStatus.FAILED),
        ],
    )
    def test_post_command(self, release, stage_class_setter, post_command_result, stage_status):
        executor = PluginReleaseExecutor(release)
        release.current_stage.reset()
        stage_class_setter.return_value = build_stage_controller(
            PluginReleaseStatus.SUCCESSFUL, post_command_result=post_command_result
        )
        assert release.current_stage.stage_id == "stage1"
        executor.execute_current_stage("")
        assert release.current_stage.stage_id == "stage1"
        assert release.current_stage.status == stage_status
