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
from django.db import transaction
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class


class ClusterViewSet(viewsets.GenericViewSet):
    """集群管理，接入相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list(self, request, *args, **kwargs):
        """
        获取集群列表

        平台管理员：可以查看到所有集群
        租户管理员：只能查看本租户创建的 & 可用的集群
        """

    @transaction.atomic(using="workloads")
    def create(self, request, *args, **kwargs):
        """
        新建集群

        平台管理员：可以创建集群，并分配给指定租户（多个）
        租户管理员：只能创建集群，并分配给本租户
        """

    @transaction.atomic(using="workloads")
    def update(self, request, *args, **kwargs):
        """
        更新集群

        平台管理员：可以更新所有集群
        租户管理员：只能更新本租户创建的集群
        """

    @transaction.atomic(using="workloads")
    def destroy(self, request, *args, **kwargs):
        """
        删除集群

        平台管理员：可以删除所有集群
        租户管理员：只能删除本租户创建的集群
        """


class ClusterAllocationPolicyViewSet(viewsets.GenericViewSet):
    """集群分配策略"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def get_queryset(self):
        """获取集群分配策略列表"""

    def list(self, request, *args, **kwargs):
        """获取集群分配策略"""

    @transaction.atomic(using="workloads")
    def create(self, request, *args, **kwargs):
        """新建集群分配策略"""

    @transaction.atomic(using="workloads")
    def update(self, request, *args, **kwargs):
        """更新集群分配策略"""
