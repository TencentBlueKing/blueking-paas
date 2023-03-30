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
import pprint
from pathlib import Path

import cattr
import yaml
from django.conf import settings
from django.core.management.base import BaseCommand

from paasng.pluginscenter import definitions, models


class Command(BaseCommand):
    help = "创建或者更新插件类型"

    def add_arguments(self, parser):
        parser.add_argument(
            "--id",
            dest="identifier",
            required=True,
            type=str,
            help=("插件类型ID"),
        )
        parser.add_argument(
            "--env",
            dest="env",
            required=True,
            type=str,
            help=("环境，可选 stag、prod"),
        )
        parser.add_argument('--dry-run', dest="dry_run", help="dry run", action="store_true")

    def handle(self, identifier, env, dry_run, *args, **options):
        file_path = Path(settings.BASE_DIR) / 'support-files' / 'plugin' / f'{identifier}-{env}.yaml'
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.load(f)

        if models.PluginDefinition.objects.filter(identifier=identifier).exists():
            self.stdout.write(self.style.WARNING(f"ID 为 {identifier} 的插件类型已经存在，将进行更新"))

        pd_data = cattr.structure(data, definitions.PluginDefinition)

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY-RUN: 创建或者更新 ID 为 {identifier} 的插件类型"))
            pprint.pp(pd_data, stream=self.stdout)
            return

        # 插件类型定义
        pd, _ = models.PluginDefinition.objects.update_or_create(
            identifier=pd_data.identifier,
            defaults={
                'name_zh_cn': pd_data.name,
                'description_zh_cn': pd_data.description,
                'docs': pd_data.docs,
                'logo': pd_data.logo,
                'administrator': pd_data.administrator,
                'approval_config': pd_data.approvalConfig,
                'release_revision': pd_data.releaseRevision,
                'release_stages': pd_data.releaseStages,
                'log_config': pd_data.logConfig,
                'features': pd_data.features,
            },
        )
        # 插件基本信息
        models.PluginBasicInfoDefinition.objects.update_or_create(
            pd=pd,
            defaults={
                "id_schema": pd_data.spec.basicInfo.id,
                "name_schema": pd_data.spec.basicInfo.name,
                "init_templates": pd_data.spec.basicInfo.initTemplates,
                "release_method": pd_data.spec.basicInfo.releaseMethod,
                "repository_group": pd_data.spec.basicInfo.repositoryGroup,
                "api": pd_data.spec.basicInfo.api,
                "extra_fields": pd_data.spec.basicInfo.extraFields,
            },
        )

        # 插件市场信息
        models.PluginMarketInfoDefinition.objects.update_or_create(
            pd=pd,
            defaults={
                "storage": pd_data.spec.marketInfo.storage,
                "category": pd_data.spec.marketInfo.category,
                "api": pd_data.spec.marketInfo.api,
                "extra_fields": pd_data.spec.marketInfo.extraFields,
            },
        )

        # 插件配置信息，非必填项
        if pd_data.spec.configInfo:
            models.PluginConfigInfoDefinition.objects.update_or_create(
                pd=pd,
                defaults={
                    "title_zh_cn": pd_data.spec.configInfo.title,
                    "description_zh_cn": pd_data.spec.configInfo.description,
                    "docs": pd_data.spec.configInfo.docs,
                    "sync_api": pd_data.spec.configInfo.syncAPI,
                    "columns": pd_data.spec.configInfo.columns,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"ID 为 {identifier} 的插件类型已更新"))
        return
