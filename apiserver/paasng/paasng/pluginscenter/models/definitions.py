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
from typing import List

from django.db import models
from translated_fields import TranslatedFieldWithFallback

from paasng.pluginscenter.definitions import (
    FieldSchema,
    PluginBackendAPI,
    PluginBackendAPIResource,
    PluginCodeTemplate,
    PluginConfigColumnDefinition,
    PluginCreateApproval,
    PluginFeature,
    PluginLogConfig,
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
PluginConfigColumnDefinitionField = make_json_field(
    "PluginConfigColumnDefinitionField", List[PluginConfigColumnDefinition]
)
PluginFeaturesField = make_json_field("PluginFeaturesField", List[PluginFeature])


class PluginDefinition(UuidAuditedModel):
    identifier = models.CharField(unique=True, max_length=64)
    name = TranslatedFieldWithFallback(models.CharField(max_length=64))
    description = TranslatedFieldWithFallback(models.TextField())
    docs = models.CharField(max_length=255)
    logo = models.CharField(max_length=255)

    administrator = models.JSONField()
    approval_config = PluginCreateApprovalField()

    release_revision: ReleaseRevisionDefinition = ReleaseRevisionDefinitionField()
    release_stages: List[ReleaseStageDefinition] = ReleaseStageDefinitionField()
    log_config: PluginLogConfig = PluginLogConfigField(null=True)
    features: List[PluginFeature] = PluginFeaturesField(default=list)


class PluginBasicInfoDefinition(AuditedModel):
    pd = models.OneToOneField(
        PluginDefinition, on_delete=models.CASCADE, db_constraint=False, related_name="basic_info_definition"
    )
    id_schema = FieldSchemaField()
    name_schema = FieldSchemaField()
    init_templates = PluginCodeTemplateListField(help_text="初始化模板")
    release_method = models.CharField(verbose_name="发布方式", max_length=16)
    repository_group = models.CharField(verbose_name="插件代码初始化仓库组", max_length=255)
    api: PluginBackendAPI = PluginBackendAPIField()
    sync_members: PluginBackendAPIResource = PluginBackendAPIResourceField(null=True)
    extra_fields = models.JSONField(default=dict)

    @classmethod
    def get_languages(cls) -> List[str]:
        """get languages declared in all plugin templates"""
        language_list = []

        plugin_templates = cls.objects.values_list('init_templates', flat=True)
        for templates in plugin_templates:
            languages = [t.language for t in templates]
            language_list.extend(languages)

        return list(set(language_list))


class PluginMarketInfoDefinition(AuditedModel):
    pd = models.OneToOneField(
        PluginDefinition, on_delete=models.CASCADE, db_constraint=False, related_name="market_info_definition"
    )
    storage = models.CharField(verbose_name="存储方式", max_length=16)
    category: PluginBackendAPIResource = PluginBackendAPIResourceField()
    api: PluginBackendAPI = PluginBackendAPIField(null=True)
    extra_fields = models.JSONField(default=dict)


class PluginConfigInfoDefinition(AuditedModel):
    pd = models.OneToOneField(
        PluginDefinition, on_delete=models.CASCADE, db_constraint=False, related_name="config_definition"
    )

    title = TranslatedFieldWithFallback(models.CharField(verbose_name="「配置管理标题」", max_length=16))
    description = TranslatedFieldWithFallback(models.TextField(default=""))
    docs = models.CharField(max_length=255, default="")
    sync_api: PluginBackendAPIResource = PluginBackendAPIResourceField(null=True)
    columns: List[PluginConfigColumnDefinition] = PluginConfigColumnDefinitionField(default=list)
