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
from typing import List, Optional

import cattr
from attrs import define
from django.db import models
from translated_fields import TranslatedFieldWithFallback

from paasng.pluginscenter.constants import PluginReleaseStatus, PluginRole, PluginStatus
from paasng.pluginscenter.definitions import PluginCodeTemplate
from paasng.utils.models import AuditedModel, BkUserField, UuidAuditedModel, make_json_field


@define
class PlainStageInfo:
    id: str
    name: str


PluginCodeTemplateField = make_json_field("PluginCodeTemplateField", PluginCodeTemplate)
StagesShortcutField = make_json_field("StagesShortcutField", List[PlainStageInfo])


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
    creator = BkUserField()
    is_deleted = models.BooleanField(default=False, help_text="是否已删除")

    class Meta:
        unique_together = ("pd", "id")


class PluginMarketInfo(AuditedModel):
    """插件市场信息"""

    plugin = models.OneToOneField(PluginInstance, on_delete=models.CASCADE, db_constraint=False)

    category = models.CharField(verbose_name="分类", max_length=16, db_index=True)
    introduction = TranslatedFieldWithFallback(models.CharField(max_length=255, verbose_name="简介"))
    description = TranslatedFieldWithFallback(models.TextField(verbose_name="详细描述", null=True))
    contact = models.TextField(verbose_name="联系人", help_text="以分号(;)分割")
    extra_fields = models.JSONField(verbose_name="额外字段")


class PluginMembership(AuditedModel):
    """插件成员"""

    plugin = models.ForeignKey(PluginInstance, on_delete=models.CASCADE, db_constraint=False)

    user = BkUserField()
    role = models.IntegerField(default=PluginRole.DEVELOPER.value)


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
                raise TypeError("get_latest_succeeded() 1 required positional argument: 'plugin'")

        try:
            return self.filter(
                plugin=plugin, status__in=[PluginReleaseStatus.PENDING, PluginReleaseStatus.INITIAL]
            ).latest('created')
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
    stages_shortcut: List[PlainStageInfo] = StagesShortcutField(help_text="发布阶段简易索引(保证顺序可靠)", null=True, default=[])
    status = models.CharField(default=PluginReleaseStatus.INITIAL, max_length=16)
    tag = models.CharField(verbose_name="标签", max_length=16, db_index=True, null=True)

    creator = BkUserField()

    objects = PluginReleaseVersionManager()

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
            next_stage, _ = PluginReleaseStage.objects.get_or_create(
                release=self,
                stage_id=stage.id,
                stage_name=stage.name,
                invoke_method=stage.invokeMethod,
                next_stage=next_stage,
            )
        self.current_stage = next_stage
        self.stages_shortcut = stages_shortcut[::-1]
        self.save(update_fields=["current_stage", "stages_shortcut", "updated"])


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
    # TODO: 完善该字段的模型
    itsm_detail = models.JSONField(verbose_name="ITSM 详情", null=True, help_text="该字段仅 invoke_method = itsm 时可用")
    api_detail = models.JSONField(verbose_name="API 详情", null=True, help_text="该字段仅 invoke_method = api 时可用")

    next_stage = models.OneToOneField("PluginReleaseStage", on_delete=models.SET_NULL, db_constraint=False, null=True)

    class Meta:
        unique_together = ("release", "stage_id")
