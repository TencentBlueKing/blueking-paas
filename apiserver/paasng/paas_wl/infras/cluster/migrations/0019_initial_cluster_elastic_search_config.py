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

import logging

from django.conf import settings
from django.db import migrations

logger = logging.getLogger(__name__)


def forwards_func(apps, schema_editor):
    """为存量集群初始化 ES 配置信息"""
    Cluster = apps.get_model("cluster", "Cluster")
    ClusterElasticSearchConfig = apps.get_model("cluster", "ClusterElasticSearchConfig")

    if not settings.ELASTICSEARCH_HOSTS:
        logger.warning("ELASTICSEARCH_HOSTS is not configured, skip initializing cluster elasticsearch config")
        return

    # 已确认只需考虑第一个 ES 配置
    conf = settings.ELASTICSEARCH_HOSTS[0]
    host, port = conf["host"], conf["port"]
    username, _, password = conf["http_auth"].partition(":")
    scheme = "https" if conf.get("use_ssl") else "http"

    for cluster in Cluster.objects.using(schema_editor.connection.alias).all():
        # 仅当集群没有配置 ES 时才初始化
        ClusterElasticSearchConfig.objects.using(
            schema_editor.connection.alias,
        ).get_or_create(
            cluster=cluster,
            defaults={
                "scheme": scheme,
                "host": host,
                "port": port,
                "username": username,
                "password": password,
                "tenant_id": cluster.tenant_id,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("cluster", "0018_initial_cluster_components"),
    ]

    operations = [migrations.RunPython(forwards_func)]
