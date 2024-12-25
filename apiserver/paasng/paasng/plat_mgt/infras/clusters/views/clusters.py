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

from django.conf import settings
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.constants import ClusterTokenType, ClusterType
from paas_wl.infras.cluster.models import APIServer, Cluster, ClusterElasticSearchConfig
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.workloads.networking.egress.cluster_state import generate_state, sync_state_to_nodes
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.infras.clusters.detect import ClusterUsageDetector
from paasng.plat_mgt.infras.clusters.serializers import (
    ClusterCreateInputSLZ,
    ClusterListOutputSLZ,
    ClusterRetrieveOutputSLZ,
    ClusterUpdateInputSLZ,
)
from paasng.plat_mgt.infras.clusters.serializers.clusters import ClusterUsageRetrieveOutputSLZ
from paasng.utils.error_codes import error_codes


class ClusterViewSet(viewsets.GenericViewSet):
    """集群管理，接入相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    lookup_field = "name"
    lookup_url_kwarg = "cluster_name"

    def get_queryset(self):
        # FIXME（多租户）根据平台/租户管理员身份，返回不同的集群列表
        return Cluster.objects.all()

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster"],
        operation_description="集群列表",
        responses={status.HTTP_200_OK: ClusterListOutputSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取集群列表"""
        clusters = self.get_queryset()
        return Response(data=ClusterListOutputSLZ(clusters, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster"],
        operation_description="获取集群详情",
        responses={status.HTTP_200_OK: ClusterRetrieveOutputSLZ()},
    )
    def retrieve(self, request, cluster_name, *args, **kwargs):
        """获取集群信息"""
        cluster = self.get_object()
        return Response(data=ClusterRetrieveOutputSLZ(cluster).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster"],
        operation_description="新建集群",
        request_body=ClusterCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: ""},
    )
    def create(self, request, *args, **kwargs):
        slz = ClusterCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        with transaction.atomic(using="workloads"):
            # 创建集群
            cluster = Cluster.objects.create(
                # 集群分划属性
                region=settings.DEFAULT_REGION_NAME,
                # FIXME（多租户）替换为用户所属租户 ID
                tenant_id="default",
                available_tenant_ids=data["available_tenant_ids"],
                # 集群基本属性
                name=data["name"],
                type=ClusterType.NORMAL,
                description=data["description"],
                ingress_config=data["ingress_config"],
                annotations=data["annotations"],
                # 认证相关配置
                ca_data=data["ca"],
                cert_data=data["cert"],
                key_data=data["key"],
                token_type=ClusterTokenType.SERVICE_ACCOUNT,
                token_value=data["token"],
                # App 默认配置（仅含创建时的默认配置，不含节点选择器等）
                container_log_dir=data["container_log_dir"],
            )
            # 创建 ApiServers
            api_servers = [APIServer(cluster=cluster, host=host) for host in data["api_servers"]]
            APIServer.objects.bulk_create(api_servers)
            # 创建 ElasticSearch 配置
            ClusterElasticSearchConfig.objects.create(cluster=cluster, **data["elastic_search_config"])

        # FIXME（多租户）添加刷新集群配置缓存逻辑

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster"],
        operation_description="更新集群",
        request_body=ClusterUpdateInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()

        slz = ClusterUpdateInputSLZ(data=request.data, context={"cur_cluster": cluster})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        # 基础配置
        cluster.available_tenant_ids = data["available_tenant_ids"]
        cluster.description = data["description"]
        cluster.ingress_config = data["ingress_config"]
        cluster.annotations = data["annotations"]

        # 集群认证信息
        cluster.ca_data = data["ca"]
        cluster.cert_data = data["cert"]
        cluster.key_data = data["key"]
        cluster.token_value = data["token"]

        # App 默认配置
        cluster.default_tolerations = data["tolerations"]
        cluster.default_node_selector = data["node_selector"]
        cluster.container_log_dir = data["container_log_dir"]

        cluster.component_preferred_namespace = data["component_preferred_namespace"]
        cluster.component_image_registry = data["component_image_registry"]
        cluster.feature_flags = data["feature_flags"]

        # 集群 ElasticSearch 配置
        es_cfg = data["elastic_search_config"]
        cluster_es_cfg = cluster.elastic_search_config
        cluster_es_cfg.scheme = es_cfg["scheme"]
        cluster_es_cfg.host = es_cfg["host"]
        cluster_es_cfg.port = es_cfg["port"]
        cluster_es_cfg.username = es_cfg["username"]
        cluster_es_cfg.password = es_cfg["password"]

        with transaction.atomic(using="workloads"):
            cluster.save()
            cluster_es_cfg.save()

            # 更新 ApiServers，采用先全部删除，再插入的方式
            cluster.api_servers.all().delete()
            api_servers = [APIServer(cluster=cluster, host=host) for host in data["api_servers"]]
            APIServer.objects.bulk_create(api_servers)

        # FIXME（多租户）添加刷新集群配置缓存逻辑

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster"],
        operation_description="删除集群",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, cluster_name, *args, **kwargs):
        # TODO（多租户）删除集群是个危险操作，需要补充审计
        cluster = self.get_object()

        # 删除集群前需要检查使用情况（分配策略，应用模块绑定等）
        state = ClusterUsageDetector(cluster).detect()
        if state.allocated_tenant_ids:
            raise error_codes.CANNOT_DELETE_CLUSTER.f(
                f"集群已被租户 {', '.join(state.allocated_tenant_ids)} 分配",
            )
        if state.bind_app_module_envs:
            raise error_codes.CANNOT_DELETE_CLUSTER.f(
                f"集群已被 {len(state.bind_app_module_envs)} 个应用部署环境绑定",
            )

        cluster.elastic_search_config.delete()
        cluster.api_servers.all().delete()
        cluster.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve_status(self, request, cluster_name, *args, **kwargs):
        """获取集群状态"""
        # FIXME（多租户）提供集群基础信息，组件状态，集群特性配置完成度

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster"],
        operation_description="获取集群使用情况",
        responses={status.HTTP_200_OK: ClusterUsageRetrieveOutputSLZ()},
    )
    def retrieve_usage(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()
        state = ClusterUsageDetector(cluster).detect()
        return Response(ClusterUsageRetrieveOutputSLZ(state).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster"],
        operation_description="同步集群节点",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def sync_nodes(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()
        client = get_client_by_cluster_name(cluster_name=cluster.name)

        ignore_labels = {"node-role.kubernetes.io/master": "true"}
        state = generate_state(cluster.region, cluster.name, client, ignore_labels)
        sync_state_to_nodes(client, state)

        return Response(status=status.HTTP_204_NO_CONTENT)