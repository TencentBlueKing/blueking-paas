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
from django.apps import apps
from django.core.management.base import BaseCommand

from paasng.accounts.models import Oauth2TokenHolder, PrivateTokenHolder


class Command(BaseCommand):
    """数据加密迁移"""

    help = "accounts 存量数据加密迁移"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            dest="model_name",
            required=False,
            help="name of the model for encryption migration",
        )

    def handle(self, **options):
        model_name = options.get("model_name")
        if model_name:
            model = apps.get_model(app_label="accounts", model_name=model_name)
            for obj in model.objects.all():
                obj.save()
        else:
            for obj in PrivateTokenHolder.objects.all():
                obj.save()
            for obj in Oauth2TokenHolder.objects.all():
                obj.save()
