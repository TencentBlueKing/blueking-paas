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

import logging
import time
from pathlib import PurePath
from typing import Dict, List, Optional

import cattr
from attrs import define
from bkpaas_auth import get_user_by_user_id
from bkstorages.backends.bkrepo import RequestError
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.utils.functional import cached_property
from pilkit.processors import ResizeToFill
from translated_fields import TranslatedFieldWithFallback

from paasng.bk_plugins.pluginscenter import constants
from paasng.bk_plugins.pluginscenter.definitions import PluginCodeTemplate, PluginoverviewPage, find_stage_by_id
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ApprovalServiceName
from paasng.core.core.storages.object_storage import plugin_logo_storage
from paasng.utils.models import AuditedModel, BkUserField, ProcessedImageField, UuidAuditedModel, make_json_field

logger = logging.getLogger(__name__)


@define
class PlainStageInfo:
    id: str
    name: str


@define
class ItsmDetail:
    sn: str
    fields: List[Dict]
    ticket_url: str


PluginCodeTemplateField = make_json_field("PluginCodeTemplateField", PluginCodeTemplate)
StagesShortcutField = make_json_field("StagesShortcutField", List[PlainStageInfo])
ItsmDetailField = make_json_field("ItsmDetailField", ItsmDetail)


def generate_plugin_logo_filename(instance: "PluginInstance", filename: str) -> str:
    """Generate uploaded logo filename"""
    suffix = PurePath(filename).suffix
    name = f"{instance.pd.identifier}/{instance.id}_{time.time_ns()}{suffix}"
    return name


class PluginInstance(UuidAuditedModel):
    """插件实例"""

    pd = models.ForeignKey("PluginDefinition", on_delete=models.SET_NULL, db_constraint=False, null=True)
    id = models.CharField(max_length=32, help_text="插件id")
    name = TranslatedFieldWithFallback(models.CharField(max_length=32))
    template: PluginCodeTemplate = PluginCodeTemplateField()
    extra_fields = models.JSONField(verbose_name="额外字段")

    language = models.CharField(verbose_name="开发语言", max_length=16, help_text="冗余字段, 用于减少查询次数")
    repo_type = models.CharField(verbose_name="源码托管类型", max_length=16, null=True)
    repository = models.CharField(max_length=255)
    status = models.CharField(
        verbose_name="插件状态",
        max_length=16,
        choices=constants.PluginStatus.get_choices(),
        default=constants.PluginStatus.WAITING_APPROVAL,
    )
    publisher = models.CharField(verbose_name="插件发布者", max_length=64, default="")
    itsm_detail: Optional[ItsmDetail] = ItsmDetailField(default=None, null=True)
    creator = BkUserField()
    is_deleted = models.BooleanField(default=False, help_text="是否已删除")

    logo = ProcessedImageField(
        storage=plugin_logo_storage,
        upload_to=generate_plugin_logo_filename,
        processors=[ResizeToFill(144, 144)],
        format="PNG",
        options={"quality": 95},
        default=None,
    )

    def get_logo_url(self) -> str:
        # 插件应用的默认 Logo 用平台统一的 Logo
        default_url = settings.PLUGIN_APP_DEFAULT_LOGO
        if self.logo:
            try:
                return self.logo.url
            except (SuspiciousOperation, RequestError):
                # 在有问题的测试环境下，个别应用的 logo 地址可能会无法生成
                logger.info("Unable to make logo url for plugin: %s/%s", self.pd.identifier, self.id)
                return default_url
        return default_url

    def get_overview_page(self) -> Optional[PluginoverviewPage]:
        if not (overview_page := self.pd.basic_info_definition.overview_page):
            return None

        if overview_page.topUrl:
            overview_page.topUrl = overview_page.topUrl.format(plugin_id=self.id)
        if overview_page.bottomUrl:
            overview_page.bottomUrl = overview_page.bottomUrl.format(plugin_id=self.id)
        if overview_page.ignoredUrl:
            overview_page.ignoredUrl = overview_page.ignoredUrl.format(plugin_id=self.id)
        return overview_page

    @property
    def can_reactivate(self) -> bool:
        return self.pd.basic_info_definition.api.reactivate is not None

    @property
    def test_versions(self):
        return self.all_versions.filter(type=constants.PluginReleaseType.TEST)

    @property
    def prod_versions(self):
        return self.all_versions.filter(type=constants.PluginReleaseType.PROD)

    @property
    def prod_releasing_versions(self):
        return self.all_versions.filter(
            type=constants.PluginReleaseType.PROD, status__in=constants.PluginReleaseStatus.running_status()
        )

    @property
    def has_test_version(self) -> bool:
        return self.pd.test_release_revision is not None

    class Meta:
        unique_together = ("pd", "id")


class PluginMarketInfo(AuditedModel):
    """插件市场信息"""

    plugin = models.OneToOneField(PluginInstance, on_delete=models.CASCADE, db_constraint=False)

    category = models.CharField(verbose_name="分类", max_length=64, db_index=True)
    introduction = TranslatedFieldWithFallback(models.CharField(max_length=255, verbose_name="简介"))
    description = TranslatedFieldWithFallback(models.TextField(verbose_name="详细描述", null=True))
    contact = models.TextField(verbose_name="联系人", help_text="以分号(;)分割")
    extra_fields = models.JSONField(verbose_name="额外字段")


class PluginReleaseVersionManager(models.Manager):
    def get_latest_succeeded(
        self, plugin: Optional["PluginInstance"] = None, type: Optional[str] = constants.PluginReleaseType.PROD
    ) -> Optional["PluginRelease"]:
        """获取最后一个成功发布的版本，默认为正式版本用于:
        1. 新建测试/版本页面：
        - 代码差异对比
        - 自动生成版本号
        """
        # 兼容关联查询(RelatedManager)的接口
        if plugin is None:
            if hasattr(self, "instance"):
                plugin = self.instance
            else:
                raise TypeError("get_latest_succeeded() 1 required positional argument: 'plugin'")

        try:
            return self.filter(plugin=plugin, status=constants.PluginReleaseStatus.SUCCESSFUL, type=type).latest(
                "created"
            )
        except self.model.DoesNotExist:
            return None

    def get_ongoing_release(self, plugin: Optional["PluginInstance"] = None) -> Optional["PluginRelease"]:
        """获取正在发布的正式版本，用于:
        1.更新市场信息时，判断是否将当前发布阶段的状态设置为成功，进入到下一步，目前仅标准运维插件使用
        2.插件列表页面:最新版本的id，用于拼装路由，TODO：让前端统一用 latest_release
        """
        # 兼容关联查询(RelatedManager)的接口
        if plugin is None:
            if hasattr(self, "instance"):
                plugin = self.instance
            else:
                raise TypeError("get_ongoing_release() 1 required positional argument: 'plugin'")

        try:
            return self.filter(
                plugin=plugin,
                status__in=constants.PluginReleaseStatus.running_status(),
                type=constants.PluginReleaseType.PROD,
            ).latest("created")
        except self.model.DoesNotExist:
            return None

    def get_latest_release(self, plugin: Optional["PluginInstance"] = None) -> Optional["PluginRelease"]:
        """获取最新的正式版本, 用于:
        1.插件列表页面:展示最新版本的信息和状态
        """
        # 兼容关联查询(RelatedManager)的接口
        if plugin is None:
            if hasattr(self, "instance"):
                plugin = self.instance
            else:
                raise TypeError("get_latest_release() 1 required positional argument: 'plugin'")

        if ongoing_release := self.get_ongoing_release(plugin):
            return ongoing_release

        try:
            return self.filter(plugin=plugin, type=constants.PluginReleaseType.PROD).latest("created")
        except self.model.DoesNotExist:
            return None


class PluginRelease(AuditedModel):
    """插件发布版本"""

    plugin = models.ForeignKey(
        PluginInstance, on_delete=models.CASCADE, db_constraint=False, related_name="all_versions"
    )
    type = models.CharField(
        verbose_name="版本类型(正式/测试)", max_length=16, choices=constants.PluginReleaseType.get_choices()
    )
    version = models.CharField(verbose_name="版本号", max_length=255)
    comment = models.TextField(verbose_name="版本日志")
    extra_fields = models.JSONField(verbose_name="额外字段")
    semver_type = models.CharField(
        verbose_name="语义化版本类型", max_length=16, null=True, help_text="该字段只用于自动生成版本号的插件"
    )

    source_location = models.CharField(verbose_name="代码仓库地址", max_length=2048)
    source_version_type = models.CharField(verbose_name="代码版本类型(branch/tag)", max_length=128, null=True)
    source_version_name = models.CharField(verbose_name="代码分支名/tag名", max_length=128, null=True)
    source_hash = models.CharField(verbose_name="代码提交哈希", max_length=128)

    current_stage = models.OneToOneField(
        "PluginReleaseStage", on_delete=models.SET_NULL, db_constraint=False, null=True
    )
    stages_shortcut: List[PlainStageInfo] = StagesShortcutField(
        help_text="发布阶段简易索引(保证顺序可靠)", null=True, default=list
    )
    status = models.CharField(default=constants.PluginReleaseStatus.INITIAL, max_length=16)
    tag = models.CharField(verbose_name="标签", max_length=16, db_index=True, null=True)
    retryable = models.BooleanField(default=True, help_text="失败后是否可重试")
    is_rolled_back = models.BooleanField(default=False, help_text="是否已回滚")
    # 灰度状态需要根据 itsm 审批单据的状态来确定，为避免每次查询灰度状态的时候都调用 itsm API，记录到 DB 中，在 itsm 回调时更新灰度状态
    # 同时，也方便前端根据”灰度状态“过滤发布版本
    gray_status = models.CharField(
        verbose_name="灰度发布状态", max_length=32, default=constants.GrayReleaseStatus.IN_GRAY
    )

    creator = BkUserField()

    objects = PluginReleaseVersionManager()

    @property
    def complete_time(self):
        if self.status not in constants.PluginReleaseStatus.running_status():
            return self.updated
        return None

    def initial_stage_set(self, force_refresh: bool = False):
        pd = self.plugin.pd
        release_stages = pd.get_release_stage_by_type(self.type)
        if not release_stages:
            return

        if self.all_stages.count() != 0:
            if not force_refresh:
                raise RuntimeError("Release 不能重复初始化")
            self.all_stages.all().delete()

        stages_shortcut = []
        next_stage = None
        for stage in release_stages[::-1]:
            stages_shortcut.append(cattr.structure({"id": stage.id, "name": stage.name}, PlainStageInfo))
            next_stage, _ = PluginReleaseStage.objects.update_or_create(
                release=self,
                stage_id=stage.id,
                stage_name=stage.name,
                invoke_method=stage.invokeMethod,
                status_polling_method=stage.statusPollingMethod,
                defaults={
                    "next_stage": next_stage,
                    "status": constants.PluginReleaseStatus.INITIAL,
                },
            )
        self.current_stage = next_stage
        self.stages_shortcut = stages_shortcut[::-1]
        self.status = constants.PluginReleaseStatus.PENDING
        self.save(update_fields=["current_stage", "stages_shortcut", "status", "updated"])

    @property
    def latest_release_strategy(self) -> Optional["PluginReleaseStrategy"]:
        if self.release_strategies.exists():
            return self.release_strategies.latest("created")
        return None

    @property
    def is_release_strategy_organization_changed(self) -> bool:
        """检查发布策略的组织是否变更"""

        # 如果没有最新的发布策略，返回 True
        latest_release_strategy = self.latest_release_strategy
        if not latest_release_strategy:
            return True

        # 找到倒数第二的发布策略
        try:
            second_release_strategy = self.release_strategies.exclude(id=latest_release_strategy.id).latest("created")
        except self.release_strategies.model.DoesNotExist:
            # 如果找不到倒数第二个策略，返回 True
            return True

        # 获取两个发布策略的组织 ID 集合
        latest_org_ids = {s.id for s in latest_release_strategy.organization}
        second_org_ids = {s.id for s in second_release_strategy.organization}

        # 前后两个组织的 ID 不完全相等
        return latest_org_ids != second_org_ids

    @property
    def is_latest(self) -> bool:
        """判断版本是否为当前最新发布成功的版本"""
        latest_release = (
            PluginRelease.objects.filter(
                plugin=self.plugin, type=self.type, status=constants.PluginReleaseStatus.SUCCESSFUL
            )
            .order_by("-created")
            .first()
        )
        return self == latest_release


class PluginReleaseStage(AuditedModel):
    """插件发布阶段"""

    release = models.ForeignKey(
        PluginRelease, on_delete=models.CASCADE, db_constraint=False, related_name="all_stages"
    )

    stage_id = models.CharField(verbose_name="阶段标识", max_length=32)
    stage_name = models.CharField(verbose_name="阶段名称", max_length=16, help_text="冗余字段, 用于减少查询次数")
    invoke_method = models.CharField(verbose_name="触发方式", max_length=16, help_text="冗余字段, 用于减少查询次数")
    status_polling_method = models.CharField(
        verbose_name="阶段的状态轮询方式",
        max_length=16,
        default=constants.StatusPollingMethod.API,
        help_text="冗余字段, 用于减少查询次数",
    )

    status = models.CharField(verbose_name="发布状态", default=constants.PluginReleaseStatus.INITIAL, max_length=16)
    fail_message = models.TextField(verbose_name="错误原因")
    itsm_detail: Optional[ItsmDetail] = ItsmDetailField(default=None, null=True)
    api_detail = models.JSONField(verbose_name="API 详情", null=True, help_text="该字段仅 invoke_method = api 时可用")
    pipeline_detail = models.JSONField(
        verbose_name="流水线构建详情", default=None, null=True, help_text="该字段仅 invoke_method = pipeline 时可用"
    )
    operator = models.CharField(verbose_name="操作人", max_length=32, null=True)

    next_stage = models.OneToOneField("PluginReleaseStage", on_delete=models.SET_NULL, db_constraint=False, null=True)

    class Meta:
        unique_together = ("release", "stage_id")

    def reset(self):
        """reset release-stage to not executed state"""
        self.status = constants.PluginReleaseStatus.INITIAL
        self.fail_message = ""
        self.itsm_detail = None
        self.api_detail = None
        self.save(update_fields=["status", "fail_message", "itsm_detail", "api_detail", "updated"])

    def update_status(self, status: constants.PluginReleaseStatus, fail_message: str = ""):
        self.status = status
        if fail_message:
            self.fail_message = fail_message
        self.save(update_fields=["status", "fail_message", "updated"])

    @cached_property
    def has_post_command(self):
        stage_definition = find_stage_by_id(self.release.plugin.pd, self.release, self.stage_id)
        if stage_definition and stage_definition.api and stage_definition.api.postCommand:
            return True
        return False


class PluginReleaseStrategy(AuditedModel):
    """插件版本的发布策略"""

    release = models.ForeignKey(
        PluginRelease, on_delete=models.CASCADE, db_constraint=False, related_name="release_strategies"
    )
    strategy = models.CharField(
        verbose_name="发布策略", max_length=32, choices=constants.ReleaseStrategy.get_choices()
    )
    bkci_project = models.JSONField(
        verbose_name="蓝盾项目ID", blank=True, null=True, help_text="格式：['1111', '222222']"
    )
    # 项目内目前不消化 organization 的格式，先不单独建模
    # [
    #     {
    #         "id": 1,
    #         "type": "user",
    #         "name": "admin",
    #         "display_name": "admin"
    #     },
    #     {
    #         "id": 3,
    #         "type": "department",
    #         "name": "xxxx部门",
    #         "display_name": null
    #     }
    # ]
    organization = models.JSONField(verbose_name="组织架构", blank=True, null=True)
    itsm_detail: Optional[ItsmDetail] = ItsmDetailField(default=None, null=True)

    def get_itsm_service_name(self, is_release_strategy_organization_changed: bool) -> str:
        """根据发布策略的设置获取对应的 ITSM 审批流程"""
        if self.strategy == constants.ReleaseStrategy.FULL:
            return ApprovalServiceName.CODECC_FULL_RELEASE_APPROVAL

        # 灰度范围包括了组织且组织信息变更了，则需要上级审批
        if self.organization and is_release_strategy_organization_changed:
            return ApprovalServiceName.CODECC_ORG_GRAY_RELEASE_APPROVAL
        return ApprovalServiceName.CODECC_GRAY_RELEASE_APPROVAL

    @cached_property
    def itsm_detail_fields(self) -> Optional[dict]:
        if not self.itsm_detail:
            return None
        return {item["key"]: item["value"] for item in self.itsm_detail.fields}

    @property
    def itsm_submitter(self):
        # 部分老的单据中没有 submitter，则使用版本的创建者
        release_creator = self.release.creator.username
        if self.itsm_detail_fields:
            return self.itsm_detail_fields.get("submitter", release_creator)
        return release_creator


class ApprovalService(UuidAuditedModel):
    """审批服务信息"""

    service_name = models.CharField(verbose_name="审批服务名称", max_length=64, unique=True)
    service_id = models.IntegerField(verbose_name="审批服务ID", help_text="用于在 ITSM 上提申请单据")


class PluginConfig(AuditedModel):
    """插件配置"""

    plugin = models.ForeignKey(PluginInstance, on_delete=models.CASCADE, db_constraint=False, related_name="configs")
    unique_key = models.CharField(verbose_name="唯一标识", max_length=64)
    row = models.JSONField(verbose_name="配置内容(1行), 格式 {'column_key': 'value'}", default=dict)

    class Meta:
        unique_together = ("plugin", "unique_key")


class PluginVisibleRange(AuditedModel):
    """插件可见范围"""

    plugin = models.OneToOneField(
        PluginInstance, on_delete=models.CASCADE, db_constraint=False, related_name="visible_range"
    )
    bkci_project = models.JSONField(verbose_name="蓝盾项目ID", default=list)
    organization = models.JSONField(verbose_name="组织架构", blank=True, null=True)
    is_in_approval = models.BooleanField(verbose_name="是否在审批中", default=False)
    itsm_detail: Optional[ItsmDetail] = ItsmDetailField(default=None, null=True)

    @cached_property
    def itsm_detail_fields(self) -> Optional[dict]:
        if not self.itsm_detail:
            return None
        return {item["key"]: item["value"] for item in self.itsm_detail.fields}

    @property
    def itsm_bkci_project(self):
        if self.itsm_detail_fields:
            return self.itsm_detail_fields.get("origin_bkci_project")
        return None

    @property
    def itsm_organization(self):
        if self.itsm_detail_fields:
            return self.itsm_detail_fields.get("origin_organization")
        return None

    @property
    def itsm_submitter(self):
        # 部分老的单据中没有 submitter，则使用插件的创建者
        plugin_creator = self.plugin.creator.username
        if self.itsm_detail_fields:
            return self.itsm_detail_fields.get("submitter", plugin_creator)
        return plugin_creator

    @classmethod
    def get_or_initialize_with_default(cls, plugin: "PluginInstance") -> "PluginVisibleRange":
        try:
            return cls.objects.get(plugin=plugin)
        except PluginVisibleRange.DoesNotExist:
            if hasattr(plugin.pd, "visible_range_definition"):
                defaults = {"organization": cattr.unstructure(plugin.pd.visible_range_definition.initial)}
            else:
                defaults = {}
        visible_range_obj, _created = cls.objects.get_or_create(plugin=plugin, defaults=defaults)
        return visible_range_obj


class OperationRecord(AuditedModel):
    """插件操作记录
    动作 (具体的) 主体
    -----------------
    新建  0.0.1  版本
    启动  web    进程
    修改         配置信息
    修改         应用市场新
    """

    plugin = models.ForeignKey(PluginInstance, on_delete=models.CASCADE, db_constraint=False)
    operator = BkUserField()
    action = models.CharField(max_length=32, choices=constants.ActionTypes.get_choices())
    specific = models.CharField(max_length=255, null=True)
    subject = models.CharField(max_length=32, choices=constants.SubjectTypes.get_choices())

    def get_display_text(self):
        action_text = constants.ActionTypes.get_choice_label(self.action)
        subject_text = constants.SubjectTypes.get_choice_label(self.subject)
        username = get_user_by_user_id(self.operator).username

        if self.specific:
            return f"{username} {action_text} {self.specific} {subject_text}"
        return f"{username} {action_text}{subject_text}"
