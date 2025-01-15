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

from paas_wl.infras.cluster.constants import ClusterComponentName

DEFAULT_COMPONENT_CONFIGS = [
    {"name": ClusterComponentName.BK_INGRESS_NGINX, "required": True},
    {"name": ClusterComponentName.BKAPP_LOG_COLLECTION, "required": True},
    {"name": ClusterComponentName.BKPAAS_APP_OPERATOR, "required": True},
    {"name": ClusterComponentName.BCS_GENERAL_POD_AUTOSCALER, "required": False},
]


def forwards_func(apps, schema_editor):
    """为存量集群初始化组件信息"""
    Cluster = apps.get_model("cluster", "Cluster")
    ClusterComponent = apps.get_model("cluster", "ClusterComponent")

    for cluster in Cluster.objects.using(schema_editor.connection.alias).all():
        components = [
            ClusterComponent(cluster=cluster, name=cfg["name"], required=cfg["required"])
            for cfg in DEFAULT_COMPONENT_CONFIGS
        ]
        ClusterComponent.objects.using(schema_editor.connection.alias).bulk_create(components)


class Migration(migrations.Migration):
    dependencies = [
        ("cluster", "0016_alter_cluster_exposed_url_type_and_more"),
    ]

    operations = [migrations.RunPython(forwards_func)]
