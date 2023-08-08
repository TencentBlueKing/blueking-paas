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

logger = logging.getLogger(__name__)


def encrypt_cluster_in_db(apps, schema_editor):
    """encrypt Cluster model in database """

    Cluster = apps.get_model('cluster', 'Cluster')

    logger.info("start encrypt Cluster in database...")
    for obj in Cluster.objects.using(schema_editor.connection.alias).all():
        obj.save()

    logger.info("Cluster encrypt done!")


class Migration(migrations.Migration):
    dependencies = [
        ('cluster', '0008_auto_20230807_1730'),
    ]

    operations = [
        migrations.RunPython(encrypt_cluster_in_db),
    ]
