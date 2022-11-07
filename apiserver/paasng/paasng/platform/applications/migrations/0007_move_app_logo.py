# -*- coding: utf-8 -*-
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
from django.db import migrations
from paasng.platform.applications.constants import ApplicationType
import logging

logger = logging.getLogger(__name__)


def forwards(apps, schema_editor):
    """Migrate all app logo data from Product to Application model"""
    Product = apps.get_model('market', 'Product')
    for product in Product.objects.all():
        if product.logo and product.logo.name:
            application = product.application
            application.logo = product.logo.name
            application.save(update_fields=['logo'])


class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forwards),
    ]

    dependencies = [
        ('applications', '0006_application_logo'),
        ('market', '0001_initial'),
    ]
