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

import json

from collections import defaultdict

from django.db import migrations

def migrate_mount_snapshot_data(apps, schema_editor):
    """将已有的 Mount 记录的 volume source 数据迁移到 MountDeploymentSnapshot 中"""
    db_alias = schema_editor.connection.alias
    Mount = apps.get_model("specs", "Mount")
    MountDeploymentSnapshot = apps.get_model("specs", "MountDeploymentSnapshot")

    # 按 module_id 分组, 收集每个模块下各环节的 source keys
    # 结构: {module_id: {env_name: set((source_type, source_name), ...)}}
    module_env_source_keys = defaultdict(lambda: defaultdict(set))

    # 绕开自定义字段 SourceConfigField 的解析, 直接读取原始数据
    qs = (
        Mount.objects.using(db_alias).extra({"raw_source_config": "source_config"})
        .values("module_id", "environment_name", "source_type", "raw_source_config")
        .iterator()
    )

    for item in qs:
        raw = item["raw_source_config"]
        source_config = json.loads(raw) if isinstance(raw, str) else (raw or {})

        source_type = item["source_type"]
        if source_type == "ConfigMap":
            source_name = (source_config.get("configMap") or {}).get("name")
        else:
            source_name = (source_config.get("persistentStorage") or {}).get("name")

        if not source_name:
            continue

        module_env_source_keys[item["module_id"]][item["environment_name"]].add((source_type, source_name))


    # 对每个模块, 分别为 stag 和 prod 生成 snapshot 记录
    # stag snapshot = stag source | _global_ source
    # prod snapshot = prod source | _global_ source
    for module_id, env_source_keys in module_env_source_keys.items():
        global_keys = env_source_keys.get("_global_", set())
        for env_name in ("stag", "prod"):
            combined_keys = env_source_keys.get(env_name, set()) | global_keys
            if not combined_keys:
                continue

            MountDeploymentSnapshot.objects.using(db_alias).update_or_create(
                module_id=module_id,
                environment_name=env_name,
                defaults={
                    "snapshot_data": [
                        {"source_type": source_type, "source_name": source_name}
                        for source_type, source_name in combined_keys
                    ]
                },
            )

class Migration(migrations.Migration):
    dependencies = [
        ("specs", "0012_mountdeploymentsnapshot"),
    ]

    operations = [
        migrations.RunPython(migrate_mount_snapshot_data, reverse_code=migrations.RunPython.noop),
    ]
