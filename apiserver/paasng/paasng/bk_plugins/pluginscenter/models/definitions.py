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

from typing import Dict, List

from django.db import models
from translated_fields import TranslatedFieldWithFallback

from paasng.bk_plugins.pluginscenter.constants import PluginBasicInfoAccessMode, PluginReleaseType
from paasng.bk_plugins.pluginscenter.definitions import (
    FieldSchema,
    PluginBackendAPI,
    PluginBackendAPIResource,
    PluginCodeTemplate,
    PluginConfigColumnDefinition,
    PluginCreateApproval,
    PluginFeature,
    PluginLogConfig,
    PluginoverviewPage,
    PluginVisibleRangeLevel,
    ReleaseRevisionDefinition,
    ReleaseStageDefinition,
)
from paasng.utils.models import AuditedModel, UuidAuditedModel, make_json_field

FieldSchemaField = make_json_field("FieldSchemaField", FieldSchema)
PluginBackendAPIField = make_json_field("PluginBackendAPIField", PluginBackendAPI)
PluginBackendAPIResourceField = make_json_field("PluginBackendAPIResourceField", PluginBackendAPIResource)
ReleaseRevisionDefinitionField = make_json_field("ReleaseRevisionDefinitionField", ReleaseRevisionDefinition)
ReleaseStageDefinitionField = make_json_field("ReleaseStageDefinitionField", List[ReleaseStageDefinition])
PluginLogConfigField = make_json_field("PluginLogConfigField", PluginLogConfig)
PluginCreateApprovalField = make_json_field("PluginCreateApprovalField", PluginCreateApproval)
PluginCodeTemplateListField = make_json_field("PluginCodeTemplateListField", List[PluginCodeTemplate])
PluginExtraFieldField = make_json_field("PluginExtraFieldField", Dict[str, FieldSchema])
PluginConfigColumnDefinitionField = make_json_field(
    "PluginConfigColumnDefinitionField", List[PluginConfigColumnDefinition]
)
PluginFeaturesField = make_json_field("PluginFeaturesField", List[PluginFeature])
PluginoverviewPageField = make_json_field("PluginoverviewPageField", PluginoverviewPage)
PluginVisibleRangeLevelField = make_json_field("PluginVisibleRangeLevelField", List[PluginVisibleRangeLevel])


class PluginDefinition(UuidAuditedModel):
    identifier = models.CharField(unique=True, max_length=64)
    name = TranslatedFieldWithFallback(models.CharField(max_length=64))
    description = TranslatedFieldWithFallback(models.TextField())
    docs = models.CharField(max_length=255)
    # 插件类型的 LOGO，仅用在创建插件页面辅助插件类型的选择
    logo = models.CharField(max_length=255)

    administrator = models.JSONField()
    approval_config = PluginCreateApprovalField()

    release_revision: ReleaseRevisionDefinition = ReleaseRevisionDefinitionField()
    release_stages: List[ReleaseStageDefinition] = ReleaseStageDefinitionField()
    log_config: PluginLogConfig = PluginLogConfigField(null=True)
    features: List[PluginFeature] = PluginFeaturesField(default=list)

    # 测试版本
    test_release_revision: ReleaseRevisionDefinition = ReleaseRevisionDefinitionField(null=True)
    test_release_stages: List[ReleaseStageDefinition] = ReleaseStageDefinitionField(null=True)

    def get_release_revision_by_type(self, type: str):
        if type == PluginReleaseType.TEST:
            return self.test_release_revision
        return self.release_revision

    def get_release_stage_by_type(self, type: str):
        if type == PluginReleaseType.TEST:
            return self.test_release_stages
        return self.release_stages


class PluginBasicInfoDefinition(AuditedModel):
    pd = models.OneToOneField(
        PluginDefinition, on_delete=models.CASCADE, db_constraint=False, related_name="basic_info_definition"
    )
    id_schema = FieldSchemaField()
    name_schema = FieldSchemaField()
    init_templates = PluginCodeTemplateListField(help_text="初始化模板")
    access_mode = models.CharField(
        verbose_name="基本信息查看模式", max_length=16, default=PluginBasicInfoAccessMode.READWRITE
    )
    release_method = models.CharField(verbose_name="发布方式", max_length=16)
    repository_group = models.CharField(verbose_name="插件代码初始化仓库组", max_length=255)
    api: PluginBackendAPI = PluginBackendAPIField()
    sync_members: PluginBackendAPIResource = PluginBackendAPIResourceField(null=True)
    extra_fields = PluginExtraFieldField(default=dict)
    extra_fields_en = PluginExtraFieldField(default=dict)
    extra_fields_order = models.JSONField(default=list)
    overview_page = PluginoverviewPageField(null=True)
    description = TranslatedFieldWithFallback(models.TextField(default=""))
    publisher_description = TranslatedFieldWithFallback(models.TextField(default=""))

    @classmethod
    def get_languages(cls) -> List[str]:
        """get languages declared in all plugin templates"""
        language_list = []

        plugin_templates = cls.objects.values_list("init_templates", flat=True)
        for templates in plugin_templates:
            languages = [t.language for t in templates]
            language_list.extend(languages)

        return list(set(language_list))


class PluginMarketInfoDefinition(AuditedModel):
    pd = models.OneToOneField(
        PluginDefinition, on_delete=models.CASCADE, db_constraint=False, related_name="market_info_definition"
    )
    storage = models.CharField(verbose_name="存储方式", max_length=16)
    category: PluginBackendAPIResource = PluginBackendAPIResourceField(null=True)
    api: PluginBackendAPI = PluginBackendAPIField(null=True)
    extra_fields = PluginExtraFieldField(default=dict)
    extra_fields_en = PluginExtraFieldField(default=dict)
    extra_fields_order = models.JSONField(default=list)


class PluginConfigInfoDefinition(AuditedModel):
    pd = models.OneToOneField(
        PluginDefinition, on_delete=models.CASCADE, db_constraint=False, related_name="config_definition"
    )

    title = TranslatedFieldWithFallback(models.CharField(verbose_name="「配置管理标题」", max_length=16))
    description = TranslatedFieldWithFallback(models.TextField(default=""))
    docs = models.CharField(max_length=255, default="")
    sync_api: PluginBackendAPIResource = PluginBackendAPIResourceField(null=True)
    columns: List[PluginConfigColumnDefinition] = PluginConfigColumnDefinitionField(default=list)


class PluginVisibleRangeDefinition(AuditedModel):
    pd = models.OneToOneField(
        PluginDefinition, on_delete=models.CASCADE, db_constraint=False, related_name="visible_range_definition"
    )
    api: PluginBackendAPI = PluginBackendAPIField(null=True)
    initial: PluginVisibleRangeLevel = PluginVisibleRangeLevelField(null=True)
