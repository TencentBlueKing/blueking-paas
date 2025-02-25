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
from typing import List

from django.conf import settings
from django.db import migrations

from paas_wl.infras.cluster.constants import ClusterAllocationPolicyCondType, ClusterAllocationPolicyType
from paas_wl.infras.cluster.entities import AllocationPrecedencePolicy, AllocationPolicy
from paasng.core.region.models import get_all_regions
from paasng.core.tenant.user import DEFAULT_TENANT_ID

logger = logging.getLogger(__name__)


def gen_allocation_policy(apps, schema_editor) -> AllocationPolicy:
    Cluster = apps.get_model("cluster", "Cluster")
    # 前置检查已经确保只有一个 region，即只有一个默认集群
    cluster = Cluster.objects.using(
        schema_editor.connection.alias,
    ).get(region=settings.DEFAULT_REGION_NAME, is_default=True)
    # 目前集群分配是不分环境的
    return AllocationPolicy(env_specific=False, clusters=[cluster.name], env_clusters=None)


def gen_allocation_precedence_policies(apps, schema_editor) -> List[AllocationPrecedencePolicy]:
    Cluster = apps.get_model("cluster", "Cluster")

    allocation_precedence_polices: List[AllocationPrecedencePolicy] = []
    # 考虑多个 region 的情况，将目前每个 region 配置的默认集群编排成分配策略
    for region in get_all_regions().keys():
        # 默认 region 留到最后作为 else 处理
        if region == settings.DEFAULT_REGION_NAME:
            continue

        cluster = Cluster.objects.using(schema_editor.connection.alias).filter(region=region, is_default=True).first()
        if not cluster:
            raise RuntimeError(f"No default cluster found in region {region}...")

        allocation_precedence_polices.append(
            AllocationPrecedencePolicy(
                # 使用 region 作为匹配规则
                matcher={ClusterAllocationPolicyCondType.REGION_IS: region},
                # 目前集群分配是不分环境的
                policy=AllocationPolicy(env_specific=False, clusters=[cluster.name], env_clusters=None),
            )
        )

    # 默认 region 的默认集群作为 else 条件，其 matcher 应该是空字典
    default_region_cluster = Cluster.objects.using(
        schema_editor.connection.alias,
    ).get(region=settings.DEFAULT_REGION_NAME, is_default=True)

    allocation_precedence_polices.append(
        AllocationPrecedencePolicy(
            matcher=dict(),
            policy=AllocationPolicy(
                env_specific=False,
                clusters=[default_region_cluster.name],
                env_clusters=None,
            ),
        )
    )

    return allocation_precedence_polices


def forwards_func(apps, schema_editor):
    """为默认租户初始化集群分配策略"""

    # 如果是多租户模式，则没有默认租户，无需初始化
    if settings.ENABLE_MULTI_TENANT_MODE:
        logger.warning("Multi-tenant mode is enabled, skip initializing cluster allocation policy")
        return

    ClusterAllocationPolicy = apps.get_model("cluster", "ClusterAllocationPolicy")

    # 如果已经存在分配策略，则跳过
    if (
        ClusterAllocationPolicy.objects.using(schema_editor.connection.alias)
        .filter(tenant_id=DEFAULT_TENANT_ID)
        .exists()
    ):
        logger.warning("Cluster allocation policy for default tenant already exists, skip...")
        return

    all_region_names = get_all_regions().keys()

    if len(all_region_names) == 0:
        # 不会出现没有 region 的情况，至少都会有一个
        raise RuntimeError("No region found, please check the region configuration")
    elif len(all_region_names) == 1:
        # 只有一个 region 的情况，走统一分配
        logger.info("Only one region found, use uniform allocation policy")
        policy_type = ClusterAllocationPolicyType.UNIFORM
        allocation_policy = gen_allocation_policy(apps, schema_editor)
        allocation_precedence_policies = []
    else:
        # 存在多个 region 的情况，走按规则分配
        logger.info("Multiple regions found, use rule-based allocation policy")
        policy_type = ClusterAllocationPolicyType.RULE_BASED
        allocation_policy = None
        allocation_precedence_policies = gen_allocation_precedence_policies(apps, schema_editor)

    ClusterAllocationPolicy.objects.using(
        schema_editor.connection.alias,
    ).create(
        type=policy_type,
        tenant_id=DEFAULT_TENANT_ID,
        allocation_policy=allocation_policy,
        allocation_precedence_policies=allocation_precedence_policies,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("cluster", "0019_initial_cluster_elastic_search_config"),
    ]

    operations = [migrations.RunPython(forwards_func)]
