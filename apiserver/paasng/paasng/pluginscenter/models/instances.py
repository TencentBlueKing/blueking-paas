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
import logging
import time
from pathlib import PurePath
from typing import Dict, List, Optional

import cattr
from attrs import define
from bkpaas_auth import get_user_by_user_id
from bkstorages.backends.bkrepo import RequestError
from django.core.exceptions import SuspiciousOperation
from django.db import models
from pilkit.processors import ResizeToFill
from translated_fields import TranslatedFieldWithFallback

from paasng.platform.core.storages.object_storage import plugin_logo_storage
from paasng.pluginscenter.constants import ActionTypes, PluginReleaseStatus, PluginStatus, SubjectTypes
from paasng.pluginscenter.definitions import PluginCodeTemplate
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


def generate_plugin_logo_filename(instance: 'PluginInstance', filename: str) -> str:
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
    repo_type = models.CharField(verbose_name='源码托管类型', max_length=16, null=True)
    repository = models.CharField(max_length=255)
    status = models.CharField(
        verbose_name="插件状态", max_length=16, choices=PluginStatus.get_choices(), default=PluginStatus.WAITING_APPROVAL
    )
    itsm_detail: Optional[ItsmDetail] = ItsmDetailField(default=None, null=True)
    creator = BkUserField()
    is_deleted = models.BooleanField(default=False, help_text="是否已删除")

    logo = ProcessedImageField(
        storage=plugin_logo_storage,
        upload_to=generate_plugin_logo_filename,
        processors=[ResizeToFill(144, 144)],
        format='PNG',
        options={'quality': 95},
        default=None,
    )

    def get_logo_url(self) -> str:
        default_url = self.pd.logo
        if self.logo:
            try:
                return self.logo.url
            except (SuspiciousOperation, RequestError):
                # 在有问题的测试环境下，个别应用的 logo 地址可能会无法生成
                logger.info("Unable to make logo url for plugin: %s/%s", self.pd.identifier, self.id)
                return default_url
        return default_url

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
    def get_latest_succeeded(self, plugin: Optional['PluginInstance'] = None) -> Optional['PluginRelease']:
        """获取最后一个成功发布的版本"""
        # 兼容关联查询(RelatedManager)的接口
        if plugin is None:
            if hasattr(self, "instance"):
                plugin = self.instance
            else:
                raise TypeError("get_latest_succeeded() 1 required positional argument: 'plugin'")

        try:
            return self.filter(plugin=plugin, status=PluginReleaseStatus.SUCCESSFUL).latest('created')
        except self.model.DoesNotExist:
            return None

    def get_ongoing_release(self, plugin: Optional['PluginInstance'] = None) -> Optional['PluginRelease']:
        """获取正在发布的版本"""
        # 兼容关联查询(RelatedManager)的接口
        if plugin is None:
            if hasattr(self, "instance"):
                plugin = self.instance
            else:
                raise TypeError("get_ongoing_release() 1 required positional argument: 'plugin'")

        try:
            return self.filter(plugin=plugin, status__in=PluginReleaseStatus.running_status()).latest('created')
        except self.model.DoesNotExist:
            return None

    def get_latest_release(self, plugin: Optional['PluginInstance'] = None) -> Optional['PluginRelease']:
        """获取最新的版本"""
        # 兼容关联查询(RelatedManager)的接口
        if plugin is None:
            if hasattr(self, "instance"):
                plugin = self.instance
            else:
                raise TypeError("get_latest_release() 1 required positional argument: 'plugin'")

        if ongoing_release := self.get_ongoing_release(plugin):
            return ongoing_release

        try:
            return self.filter(plugin=plugin).latest('created')
        except self.model.DoesNotExist:
            return None


class PluginRelease(AuditedModel):
    """插件发布版本"""

    plugin = models.ForeignKey(
        PluginInstance, on_delete=models.CASCADE, db_constraint=False, related_name="all_versions"
    )
    type = models.CharField(verbose_name="版本类型(正式/测试)", max_length=16)
    version = models.CharField(verbose_name='版本号', max_length=255)
    comment = models.TextField(verbose_name="版本日志")
    extra_fields = models.JSONField(verbose_name="额外字段")
    semver_type = models.CharField(verbose_name="语义化版本类型", max_length=16, null=True, help_text="该字段只用于自动生成版本号的插件")

    source_location = models.CharField(verbose_name="代码仓库地址", max_length=2048)
    source_version_type = models.CharField(verbose_name="代码版本类型(branch/tag)", max_length=128, null=True)
    source_version_name = models.CharField(verbose_name="代码分支名/tag名", max_length=128, null=True)
    source_hash = models.CharField(verbose_name="代码提交哈希", max_length=128)

    current_stage = models.OneToOneField(
        "PluginReleaseStage", on_delete=models.SET_NULL, db_constraint=False, null=True
    )
    stages_shortcut: List[PlainStageInfo] = StagesShortcutField(help_text="发布阶段简易索引(保证顺序可靠)", null=True, default=list)
    status = models.CharField(default=PluginReleaseStatus.INITIAL, max_length=16)
    tag = models.CharField(verbose_name="标签", max_length=16, db_index=True, null=True)
    retryable = models.BooleanField(default=True, help_text="失败后是否可重试")

    creator = BkUserField()

    objects = PluginReleaseVersionManager()

    @property
    def complete_time(self):
        if self.status not in PluginReleaseStatus.running_status():
            return self.updated
        return None

    def initial_stage_set(self, force_refresh: bool = False):
        pd = self.plugin.pd
        if not pd.release_stages:
            return

        if self.all_stages.count() != 0:
            if not force_refresh:
                raise Exception("Release 不能重复初始化")
            self.all_stages.all().delete()

        stages_shortcut = []
        next_stage = None
        for stage in pd.release_stages[::-1]:
            stages_shortcut.append(cattr.structure({"id": stage.id, "name": stage.name}, PlainStageInfo))
            next_stage, _ = PluginReleaseStage.objects.update_or_create(
                release=self,
                stage_id=stage.id,
                stage_name=stage.name,
                invoke_method=stage.invokeMethod,
                defaults={
                    "next_stage": next_stage,
                    "status": PluginReleaseStatus.INITIAL,
                },
            )
        self.current_stage = next_stage
        self.stages_shortcut = stages_shortcut[::-1]
        self.status = PluginReleaseStatus.PENDING
        self.save(update_fields=["current_stage", "stages_shortcut", "status", "updated"])


class PluginReleaseStage(AuditedModel):
    """插件发布阶段"""

    release = models.ForeignKey(
        PluginRelease, on_delete=models.CASCADE, db_constraint=False, related_name="all_stages"
    )

    stage_id = models.CharField(verbose_name="阶段标识", max_length=32)
    stage_name = models.CharField(verbose_name="阶段名称", max_length=16, help_text="冗余字段, 用于减少查询次数")
    invoke_method = models.CharField(verbose_name="触发方式", max_length=16, help_text="冗余字段, 用于减少查询次数")

    status = models.CharField(verbose_name="发布状态", default=PluginReleaseStatus.INITIAL, max_length=16)
    fail_message = models.TextField(verbose_name="错误原因")
    itsm_detail: Optional[ItsmDetail] = ItsmDetailField(default=None, null=True)
    api_detail = models.JSONField(verbose_name="API 详情", null=True, help_text="该字段仅 invoke_method = api 时可用")

    next_stage = models.OneToOneField("PluginReleaseStage", on_delete=models.SET_NULL, db_constraint=False, null=True)

    class Meta:
        unique_together = ("release", "stage_id")

    def reset(self):
        """reset release-stage to not executed state"""
        self.status = PluginReleaseStatus.INITIAL
        self.fail_message = ""
        self.itsm_detail = None
        self.api_detail = None
        self.save(update_fields=["status", "fail_message", "itsm_detail", "api_detail", "updated"])

    def update_status(self, status: PluginReleaseStatus, fail_message: str = ""):
        self.status = status
        if fail_message:
            self.fail_message = fail_message
        self.save(update_fields=["status", "fail_message", "updated"])


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
    action = models.CharField(max_length=32, choices=ActionTypes.get_choices())
    specific = models.CharField(max_length=255, null=True)
    subject = models.CharField(max_length=32, choices=SubjectTypes.get_choices())

    def get_display_text(self):
        action_text = ActionTypes.get_choice_label(self.action)
        subject_text = SubjectTypes.get_choice_label(self.subject)
        username = get_user_by_user_id(self.operator).username

        if self.specific:
            return f"{username} {action_text} {self.specific} {subject_text}"
        return f"{username} {action_text}{subject_text}"
