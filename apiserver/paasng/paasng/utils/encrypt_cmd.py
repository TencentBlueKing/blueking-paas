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
from blue_krill.models.fields import EncryptField
from django.apps import apps
from django.core.management.base import BaseCommand


class ReEncryptCommand(BaseCommand):
    help = "存量数据加密迁移"

    app_label: str = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "--app_label",
            dest="app_label",
            default=self.app_label,
            help="name of the model for encryption migration",
        )

        parser.add_argument(
            "--model",
            dest="model_name",
            default="",
            help="name of the model for encryption migration",
        )

        parser.add_argument("--no-dry-run", dest="dry_run", help="dry run", action="store_false")

    def handle(self, app_label: str, model_name: str, dry_run: bool = True, **options):
        models = self._get_model_classes(model_name)
        for model_class in models:
            self.refresh_encrypt_fields(model_class, dry_run=dry_run)

    def refresh_encrypt_fields(self, model_class, dry_run: bool = True):
        update_fields = [field.name for field in model_class._meta.fields if isinstance(field, EncryptField)]
        if update_fields:
            for instance in model_class.objects.all():
                if not dry_run:
                    instance.save(update_fields=update_fields)
                else:
                    self.stdout.write(self.style.NOTICE(f"DRY-RUN: refreshing EncryptField for {instance}"))

    def _get_model_classes(self, model_name: str):
        if not self.app_label:
            return apps.get_models()

        cfg = apps.get_app_config(self.app_label)
        if model_name:
            return [cfg.get_model(model_name)]
        return cfg.get_models()
