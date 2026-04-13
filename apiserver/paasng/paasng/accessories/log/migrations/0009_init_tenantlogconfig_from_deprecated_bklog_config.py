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

# 历史兼容 migration, 从已被废弃的 BKLOG_CONFIG 配置项, 初始化为默认租户的 TenantLogConfig 记录

import datetime

from paasng.settings import settings
from django.db import migrations
from django.utils.timezone import get_default_timezone
from paasng.core.tenant.user import get_init_tenant_id

BKLOG_TIME_ZONE = settings.get("BKLOG_TIME_ZONE")
## 日志平台存储集群 ID
BKLOG_STORAGE_CLUSTER_ID = settings.get("BKLOG_STORAGE_CLUSTER_ID")
## 日志保存时间（天数），默认值 14
BKLOG_RETENTION = int(settings.get("BKLOG_RETENTION", 14))
## Elasticsearch 索引分片数，默认值 1
BKLOG_ES_SHARDS = int(settings.get("BKLOG_ES_SHARDS", 1))
## 存储副本数，默认值 1
BKLOG_STORAGE_REPLICAS = int(settings.get("BKLOG_STORAGE_REPLICAS", 1))
BKLOG_CONFIG = settings.get(
    "BKLOG_CONFIG",
    {
        "TIME_ZONE": BKLOG_TIME_ZONE,
        "STORAGE_CLUSTER_ID": BKLOG_STORAGE_CLUSTER_ID,
        "RETENTION": BKLOG_RETENTION,
        "ES_SHARDS": BKLOG_ES_SHARDS,
        "STORAGE_REPLICAS": BKLOG_STORAGE_REPLICAS,
    },
)


def get_time_zone() -> int:
    # 历史兼容，默认使用 django 的时区设置
    time_zone = BKLOG_CONFIG.get("TIME_ZONE")
    if time_zone is not None:
        return time_zone

    tz = get_default_timezone()
    return int(tz.utcoffset(datetime.datetime.now()).total_seconds() // 60 // 60)


def init_tenant_log_config(apps, schema_editor):
    tenant_log_config = apps.get_model("log", "TenantLogConfig")
    storage_cluster_id = BKLOG_CONFIG.get("STORAGE_CLUSTER_ID")

    if storage_cluster_id is None:
        return

    tenant_log_config.objects.get_or_create(
        tenant_id=get_init_tenant_id(),
        defaults={
            "storage_cluster_id": storage_cluster_id,
            "retention": BKLOG_CONFIG.get("RETENTION"),
            "es_shards": BKLOG_CONFIG.get("ES_SHARDS"),
            "storage_replicas": BKLOG_CONFIG.get("STORAGE_REPLICAS"),
            "time_zone": get_time_zone(),
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("log", "0008_tenantlogconfig"),
    ]

    operations = [
        migrations.RunPython(init_tenant_log_config, reverse_code=migrations.RunPython.noop),
    ]
