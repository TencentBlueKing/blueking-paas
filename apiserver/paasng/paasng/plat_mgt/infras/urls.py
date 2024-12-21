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

from paasng.utils.basic import re_path

from . import views

urlpatterns = [
    re_path(
        "api/plat-mgt/infras/clusters/",
        views.ClusterViewSet.as_view({"post": "create", "get": "list"}),
        name="plat_mgt.infras.cluster.bulk",
    ),
    re_path(
        "api/plat-mgt/infras/clusters/<str:cluster_id>/",
        views.ClusterViewSet.as_view({"put": "update", "delete": "destroy"}),
        name="plat_mgt.infras.cluster.detail",
    ),
    re_path(
        "api/plat-mgt/infras/cluster-allocation-policies/",
        views.ClusterAllocationPolicyViewSet.as_view({"post": "create", "get": "list"}),
        name="plat_mgt.infras.cluster_allocation_policy.bulk",
    ),
    re_path(
        "api/plat-mgt/infras/cluster-allocation-policies/<str:policy_id>/",
        views.ClusterAllocationPolicyViewSet.as_view({"put": "update"}),
        name="plat_mgt.infras.cluster_allocation_policy.detail",
    ),
]
