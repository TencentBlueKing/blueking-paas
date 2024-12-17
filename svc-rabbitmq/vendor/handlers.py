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

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from paas_service.models import Plan

from vendor.models import Cluster


@receiver(post_save, sender=Plan)
def create_related_cluster(sender, instance: Plan, created, **kwargs):
    Cluster.objects.update_or_create_by_plan(plan=instance)


@receiver(post_delete, sender=Plan)
def delete_related_cluster(sender, instance: Plan, **kwargs):
    Cluster.objects.delete_by_plan(plan=instance)
