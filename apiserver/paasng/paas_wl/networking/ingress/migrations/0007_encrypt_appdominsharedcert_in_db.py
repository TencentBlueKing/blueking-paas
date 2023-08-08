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

from django.db import migrations
from paasng.platform.core.storages.dbrouter import skip_if_found_record

logger = logging.getLogger(__name__)


def encrypt_appdomainsharedcert_in_db(apps, schema_editor):
    """encrypt AppDomainSharedCert model in database """

    AppDomainSharedCert = apps.get_model('ingress', 'AppDomainSharedCert')

    logger.info("start encrypt AppDomainSharedCert in database...")
    for obj in AppDomainSharedCert.objects.using(schema_editor.connection.alias).all():
        obj.save()

    logger.info("AppDomainSharedCert encrypt done!")


# 由于架构调整, 该 DjangoApp 从 services 重命名为 ingress
# 为避免 migrations 重复执行, 使用 skip_if_found_record 声明该 migration 的历史名称
# 如果 django_migrations 表中存在重命名前的执行记录, 则跳过执行该 Migration
@skip_if_found_record(sentinel=("services", "0006_encrypt_appdominsharedcert_in_db.py"))
class Migration(migrations.Migration):
    dependencies = [
        ('ingress', '0006_auto_20230807_1730'),
    ]

    operations = [
        migrations.RunPython(encrypt_appdomainsharedcert_in_db),
    ]