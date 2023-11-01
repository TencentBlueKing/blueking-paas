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
from django.utils.translation import gettext as _

from paasng.bk_plugins.pluginscenter import constants
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.models import PluginRelease
from paasng.bk_plugins.pluginscenter.releases.stages import init_stage_controller
from paasng.bk_plugins.pluginscenter.tasks import poll_stage_status
from paasng.bk_plugins.pluginscenter.thirdparty import release as release_api


class PluginReleaseExecutor:
    """ReleaseExecutor is controlling the lifecycle of PluginRelease and PluginReleaseStage"""

    def __init__(self, release: PluginRelease):
        self.release = release

    def initial(self, operator: str):
        """初始化版本发布并执行第一个发布阶段"""
        self.release.initial_stage_set()

        release_api.create_release(
            pd=self.release.plugin.pd, instance=self.release.plugin, version=self.release, operator=operator
        )

        self.execute_current_stage(operator=operator)

    def enter_next_stage(self, operator: str):
        """进入下一个发布阶段: 切换 release.current_stage 至 next_stage 并执行
        只有 release.current_stage 执行成功时, 才可以进入下一个阶段
        """
        stage = self.release.current_stage
        if stage.status != constants.PluginReleaseStatus.SUCCESSFUL:
            raise error_codes.EXECUTE_STAGE_ERROR.f(_("当前阶段未执行成功, 不允许进入下一阶段"))

        next_stage = stage.next_stage
        if next_stage is None:
            raise error_codes.EXECUTE_STAGE_ERROR.f(_("不存在下一阶段"))

        if next_stage.status != constants.PluginReleaseStatus.INITIAL:
            raise error_codes.EXECUTE_STAGE_ERROR.f(_("下一阶段已被执行, 不能重复触发已执行的阶段"))

        self.release.current_stage = next_stage
        self.release.save()
        self.execute_current_stage(operator=operator)

    def rerun_current_stage(self, operator: str):
        """重新执行当前发布阶段: 重置 release.current_stage 后重新执行 release.current_stage
        只有 release.current_stage 执行失败时, 才可以重新执行当前阶段
        """
        current_stage = self.release.current_stage
        if current_stage.status not in constants.PluginReleaseStatus.abnormal_status():
            raise error_codes.CANNOT_RERUN_ONGOING_STEPS

        if not self.release.retryable:
            raise error_codes.CANNOT_RERUN_ONGOING_STEPS.f(_("如需发布请创建新的版本"))

        current_stage.reset()
        self.release.status = constants.PluginReleaseStatus.PENDING
        self.release.save()
        self.execute_current_stage(operator=operator)

    def execute_current_stage(self, operator: str):
        """执行当前发布阶段: 仅执行 release.current_stage, 不修改 release 状态"""
        self.release.refresh_from_db()
        current_stage = self.release.current_stage
        if current_stage.status != constants.PluginReleaseStatus.INITIAL:
            raise error_codes.EXECUTE_STAGE_ERROR.f(_("当前阶段已被执行, 不能重复触发已执行的阶段"))

        init_stage_controller(current_stage).execute(operator)
        current_stage.operator = operator
        current_stage.save(update_fields=["operator"])
        current_stage.refresh_from_db()
        # 设置步骤状态为 Pending, 避免被重复执行
        if current_stage.status == constants.PluginReleaseStatus.INITIAL:
            current_stage.update_status(constants.PluginReleaseStatus.PENDING)

        poll_stage_status(
            plugin=self.release.plugin,
            release=self.release,
            stage=current_stage,
        )

    def back_to_previous_stage(self, operator: str):
        """回滚当前发布阶段至上一阶段: 重置 release.current_stage, 并将 release.current_stage 设置成 previous_stage
        ITSM 单据审批中不能返回上一步
        """
        if self.release.status == constants.PluginReleaseStatus.SUCCESSFUL:
            raise error_codes.CANNOT_ROLLBACK_CURRENT_STEP.f(_("当前发布流程已结束"))

        if not self.release.retryable:
            raise error_codes.CANNOT_ROLLBACK_CURRENT_STEP.f(_("当前插件类型不支持重置历史版本, 如需发布请创建新的版本"))

        current_stage = self.release.current_stage
        if (
            current_stage.invoke_method == constants.ReleaseStageInvokeMethod.ITSM
            and current_stage.status in constants.PluginReleaseStatus.running_status()
        ):
            raise error_codes.CANNOT_ROLLBACK_CURRENT_STEP.f(_("请先撤回审批单据, 再返回上一步"))
        if (
            current_stage.invoke_method == constants.ReleaseStageInvokeMethod.DEPLOY_API
            and current_stage.status in constants.PluginReleaseStatus.running_status()
        ):
            raise error_codes.CANNOT_ROLLBACK_CURRENT_STEP.f(_("请等待部署完成, 再返回上一步"))

        previous_stage_id = None
        for stage in self.release.stages_shortcut:
            if stage.id == current_stage.stage_id:
                break
            previous_stage_id = stage.id

        if previous_stage_id is None:
            raise error_codes.CANNOT_ROLLBACK_CURRENT_STEP
        previous_stage = self.release.all_stages.get(stage_id=previous_stage_id)
        current_stage.reset()
        self.release.current_stage = previous_stage
        self.release.status = constants.PluginReleaseStatus.PENDING
        self.release.save()

    def reset_release(self, operator: str):
        """重置当前发布版本"""
        if self.release.status not in constants.PluginReleaseStatus.abnormal_status():
            raise error_codes.CANNOT_RESET_RELEASE.f(_("状态异常: {}").format(self.release.status))

        if not self.release.retryable:
            raise error_codes.CANNOT_RESET_RELEASE.f(_("当前插件类型不支持重置历史版本, 如需发布请创建新的版本"))

        self.release.initial_stage_set(force_refresh=True)
        self.execute_current_stage(operator=operator)

    def cancel_release(self, operator: str):
        """取消发布"""
        if self.release.status not in constants.PluginReleaseStatus.running_status():
            raise error_codes.CANNOT_CANCEL_RELEASE.f(_("当前状态({})不支持取消发布").format(self.release.status))

        current_stage = self.release.current_stage
        if (
            current_stage.invoke_method == constants.ReleaseStageInvokeMethod.ITSM
            and current_stage.status in constants.PluginReleaseStatus.running_status()
        ):
            raise error_codes.CANNOT_CANCEL_RELEASE.f(_("请到 ITSM 撤回审批单据"))
        current_stage.update_status(constants.PluginReleaseStatus.INTERRUPTED, fail_message=_("用户主动终止发布"))
