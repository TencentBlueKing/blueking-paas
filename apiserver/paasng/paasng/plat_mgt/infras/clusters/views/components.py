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

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class


class ClusterComponentViewSet(viewsets.GenericViewSet):
    """集群组件管理"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list(self, request, cluster_name, *args, **kwargs):
        """获取集群组件列表"""
        # FIXME 根据集群 ID 获取集群组件列表

    def upsert(self, request, cluster_name, component_name, *args, **kwargs):
        """更新或新建集群组件"""
        # FIXME 根据集群 ID 和组件名称更新或新建集群组件
