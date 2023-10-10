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

from blue_krill.encrypt.handler import EncryptHandler
from blue_krill.encrypt.utils import get_default_secret_key
from django.db import migrations

logger = logging.getLogger(__name__)


def encrypt_client_secret_in_db(apps, schema_editor):
    """encrypt client secret in database before change
    client_secret field to EncryptField to avoid decode error"""

    SourceTypeSpecConfig = apps.get_model('sourcectl', 'SourceTypeSpecConfig')
    encrypt_handler = EncryptHandler(secret_key=get_default_secret_key())

    logger.info("start encrypt client secret in database...")
    for cfg in SourceTypeSpecConfig.objects.all():
        cfg.client_secret = encrypt_handler.encrypt(cfg.client_secret)
        cfg.save(update_fields=['client_secret'])

    logger.info("client secret encrypt done!")


class Migration(migrations.Migration):
    dependencies = [
        ('sourcectl', '0008_auto_20220909_1452'),
    ]

    operations = [
        migrations.RunPython(encrypt_client_secret_in_db),
    ]
