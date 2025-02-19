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

from django.urls import path

from paasng.plat_mgt.infras.clusters import views

urlpatterns = [
    path(
        "api/plat_mgt/infras/clusters/",
        views.ClusterViewSet.as_view({"post": "create", "get": "list"}),
        name="plat_mgt.infras.cluster.list_create",
    ),
    path(
        "api/plat_mgt/infras/clusters/<str:cluster_name>/",
        views.ClusterViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="plat_mgt.infras.cluster.retrieve_update_destroy",
    ),
    # 集群默认特性标记
    path(
        "api/plat_mgt/infras/clusters/<str:cluster_name>/default_feature_flags/",
        views.ClusterViewSet.as_view({"get": "retrieve_default_feature_flags"}),
        name="plat_mgt.infras.cluster.default_feature_flags",
    ),
    # 集群状态
    path(
        "api/plat_mgt/infras/clusters/<str:cluster_name>/status/",
        views.ClusterViewSet.as_view({"get": "retrieve_status"}),
        name="plat_mgt.infras.cluster.status",
    ),
    # 集群使用情况
    path(
        "api/plat_mgt/infras/clusters/<str:cluster_name>/allocation_state/",
        views.ClusterViewSet.as_view({"get": "retrieve_allocation_state"}),
        name="plat_mgt.infras.cluster.allocation_state",
    ),
    # 集群节点同步
    path(
        "api/plat_mgt/infras/clusters/<str:cluster_name>/operations/sync_nodes/",
        views.ClusterViewSet.as_view({"post": "sync_nodes"}),
        name="plat_mgt.infras.cluster.sync_nodes",
    ),
    # 集群组件安装信息
    path(
        "api/plat_mgt/infras/clusters/<str:cluster_name>/components/",
        views.ClusterComponentViewSet.as_view({"get": "list"}),
        name="plat_mgt.infras.cluster.component.list",
    ),
    # 单一集群组件相关操作
    path(
        "api/plat_mgt/infras/clusters/<str:cluster_name>/components/<str:component_name>/",
        views.ClusterComponentViewSet.as_view({"post": "upsert", "get": "retrieve"}),
        name="plat_mgt.infras.cluster.component.upsert_retrieve",
    ),
    path(
        "api/plat_mgt/infras/clusters/<str:cluster_name>/components/<str:component_name>/operations/diff_version/",
        views.ClusterComponentViewSet.as_view({"get": "diff_version"}),
        name="plat_mgt.infras.cluster.component.diff_version",
    ),
    path(
        "api/plat_mgt/infras/cluster_allocation_policies/",
        views.ClusterAllocationPolicyViewSet.as_view({"post": "create", "get": "list"}),
        name="plat_mgt.infras.cluster_allocation_policy.list_create",
    ),
    path(
        "api/plat_mgt/infras/cluster_allocation_policies/<str:policy_id>/",
        views.ClusterAllocationPolicyViewSet.as_view({"put": "update"}),
        name="plat_mgt.infras.cluster_allocation_policy.update",
    ),
    # 可选集群特性
    path(
        "api/plat_mgt/infras/cluster_feature_flags/",
        views.ClusterFeatureFlagViewSet.as_view({"get": "list"}),
        name="plat_mgt.infras.cluster_feature_flag.list",
    ),
    # BCS 项目列表
    path(
        "api/plat_mgt/infras/bcs/projects/",
        views.BCSResourceViewSet.as_view({"get": "list_projects"}),
        name="plat_mgt.infras.bcs.project.list",
    ),
    # BCS 集群列表
    path(
        "api/plat_mgt/infras/bcs/projects/<str:project_id>/clusters/",
        views.BCSResourceViewSet.as_view({"get": "list_clusters"}),
        name="plat_mgt.infras.bcs.cluster.list",
    ),
]
