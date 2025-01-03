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

from django.db import migrations


def forwards_func(apps, schema_editor):
    """将 APIServer 中的 overridden_hostname 迁移到 Cluster 中的 assert_hostname 字段"""

    Cluster = apps.get_model("cluster", "Cluster")
    APIServer = apps.get_model("cluster", "APIServer")

    for cluster in Cluster.objects.using(schema_editor.connection.alias).all():
        api_servers = APIServer.objects.using(schema_editor.connection.alias).filter(cluster=cluster)

        overridden_hostnames = set(api_servers.values_list("overridden_hostname", flat=True))
        # 如果 api_servers 有不同的 overridden_hostname 时需要手动处理，得抛出异常
        if len(overridden_hostnames) > 1:
            raise ValueError(
                f"Cluster {cluster.name} api_servers has multiple overridden hostnames: {overridden_hostnames}"
            )

        # 取出唯一的 overridden_hostname，如果不是 None / ""，则赋值给 cluster.assert_hostname
        overridden_hostname = overridden_hostnames.pop() if overridden_hostnames else None
        if not overridden_hostname:
            continue

        cluster.assert_hostname = overridden_hostname
        cluster.save()


class Migration(migrations.Migration):
    dependencies = [
        ("cluster", "0013_cluster_assert_hostname"),
    ]

    operations = [migrations.RunPython(forwards_func)]
