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
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from paas_service.models import Plan

from vendor.models import Cluster, ClusterConfig
from vendor.serializers import PlanConfigSerializer

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Plan)
def create_related_cluster(sender, instance: Plan, created, **kwargs):
    plan_config = json.loads(instance.config)
    slz = PlanConfigSerializer(data=plan_config)
    if not slz.is_valid():
        logger.error("serialize plan config error: %s", slz.errors)
        return
    config = slz.data

    cluster_config = ClusterConfig(
        name=f"{instance.name}-cluster",
        host=config["host"],
        port=config["port"],
        management_api=config["management_api"],
        admin=config["admin"],
        password=config["password"],
        cluster_version=config["cluster_version"],
        plan_id=instance.uuid,
        cluster_id=plan_config.get("cluster_id"),
    )

    cluster, created = Cluster.objects.update_or_create_by_cluster_config(cluster_config)

    if created:
        plan_config["cluster_id"] = cluster.id
        instance.config = json.dumps(plan_config)
        instance.save(update_fields=["config"])


@receiver(post_delete, sender=Plan)
def delete_related_cluster(sender, instance: Plan, **kwargs):
    Cluster.objects.delete_by_plan(plan=instance)
