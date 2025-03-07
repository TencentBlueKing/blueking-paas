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

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.constants import (
    DEFAULT_COMPONENT_CONFIGS,
    ClusterFeatureFlag,
    ClusterTokenType,
    ClusterType,
)
from paas_wl.infras.cluster.models import APIServer, Cluster, ClusterComponent, ClusterElasticSearchConfig
from paas_wl.infras.resources.base.base import get_client_by_cluster_name, invalidate_global_configuration_pool
from paas_wl.workloads.networking.egress.cluster_state import generate_state, sync_state_to_nodes
from paas_wl.workloads.networking.entrance.constants import AddressType
from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.bcs.client import BCSClient
from paasng.infras.bcs.exceptions import BCSGatewayServiceError
from paasng.infras.bk_user.client import BkUserClient
from paasng.plat_mgt.infras.clusters.k8s import check_k8s_accessible
from paasng.plat_mgt.infras.clusters.serializers import (
    ClusterCreateInputSLZ,
    ClusterDefaultFeatureFlagsRetrieveOutputSLZ,
    ClusterListOutputSLZ,
    ClusterRetrieveOutputSLZ,
    ClusterUpdateInputSLZ,
    ClusterUsageRetrieveOutputSLZ,
)
from paasng.plat_mgt.infras.clusters.state import ClusterAllocationGetter
from paasng.platform.modules.constants import ExposedURLType
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class ClusterViewSet(viewsets.GenericViewSet):
    """集群管理，接入相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    lookup_field = "name"
    lookup_url_kwarg = "cluster_name"

    def get_queryset(self):
        # FIXME: (多租户) 根据平台/租户管理员身份，返回不同的集群列表
        return Cluster.objects.all()

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="集群列表",
        responses={status.HTTP_200_OK: ClusterListOutputSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取集群列表"""
        clusters = self.get_queryset()
        user_tenant_id = get_tenant(request.user).id
        tenants = BkUserClient(user_tenant_id).list_tenants()
        context = {"tenant_name_map": {t.id: t.name for t in tenants}}
        return Response(data=ClusterListOutputSLZ(clusters, context=context, many=True).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="获取集群详情",
        responses={status.HTTP_200_OK: ClusterRetrieveOutputSLZ()},
    )
    def retrieve(self, request, cluster_name, *args, **kwargs):
        """获取集群信息"""
        cluster: Cluster = self.get_object()

        context = {}
        if cluster.bcs_project_id and cluster.bcs_cluster_id:
            # 对来源于 BCS 的集群，需要获取 BCS 项目和集群名称
            client = BCSClient(get_tenant(request.user).id, request.user.username)

            try:
                bcs_project = client.get_auth_project(cluster.bcs_project_id)
                bcs_cluster = client.get_cluster(cluster.bcs_project_id, cluster.bcs_cluster_id)
            except BCSGatewayServiceError as e:
                logger.warning(
                    "username %s get bcs project %s, cluster %s error: %s",
                    request.user.username,
                    cluster.bcs_project_id,
                    cluster.bcs_cluster_id,
                    e,
                )
            else:
                if bcs_project:
                    context["bcs_project_name"] = bcs_project.name
                    context["bk_biz_name"] = bcs_project.businessName
                if bcs_cluster:
                    context["bcs_cluster_name"] = bcs_cluster.clusterName

        return Response(data=ClusterRetrieveOutputSLZ(cluster, context=context).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="新建集群",
        request_body=ClusterCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: ""},
    )
    def create(self, request, *args, **kwargs):
        cur_tenant_id = get_tenant(request.user).id

        slz = ClusterCreateInputSLZ(
            data=request.data,
            context={"cur_tenant_id": cur_tenant_id},
        )
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        cert, ca, key, token = data["cert"], data["ca"], data["key"], data["token"]
        api_servers = data["api_servers"]

        if not check_k8s_accessible(api_servers, ca=ca, cert=cert, key=key, token=token):
            raise error_codes.CANNOT_CREATE_CLUSTER.f(_("集群无法访问，请检查配置"))

        with transaction.atomic(using="workloads"):
            # 创建集群
            cluster = Cluster.objects.create(
                # 集群分划属性
                region=settings.DEFAULT_REGION_NAME,
                tenant_id=cur_tenant_id,
                available_tenant_ids=data["available_tenant_ids"],
                # 集群基本属性
                name=data["name"],
                type=ClusterType.NORMAL,
                description=data["description"],
                ingress_config=data["ingress_config"],
                annotations=data["annotations"],
                # 认证相关配置
                ca_data=ca,
                cert_data=cert,
                key_data=key,
                token_type=ClusterTokenType.SERVICE_ACCOUNT,
                token_value=token,
                # App 默认配置（仅含创建时的默认配置，不含节点选择器等）
                container_log_dir=data["container_log_dir"],
            )
            # 创建 ApiServers
            APIServer.objects.bulk_create(
                [APIServer(cluster=cluster, host=host, tenant_id=cluster.tenant_id) for host in api_servers]
            )
            # 创建集群组件配置
            ClusterComponent.objects.bulk_create(
                [
                    ClusterComponent(cluster=cluster, name=cfg["name"], required=cfg["required"])
                    for cfg in DEFAULT_COMPONENT_CONFIGS
                ]
            )
            # 创建 ElasticSearch 配置
            ClusterElasticSearchConfig.objects.create(
                cluster=cluster, tenant_id=cluster.tenant_id, **data["elastic_search_config"]
            )

        # 新添加集群后，需要刷新配置池
        invalidate_global_configuration_pool()

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
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
        cluster.exposed_url_type = (
            ExposedURLType.SUBPATH if data["app_address_type"] == AddressType.SUBPATH else ExposedURLType.SUBDOMAIN
        )
        cluster.ingress_config = data["ingress_config"]
        cluster.annotations = data["annotations"]

        cert, ca, key, token = data["cert"], data["ca"], data["key"], data["token"]
        api_servers = data["api_servers"]

        # 检查集群认证信息 & APIServers 是否被修改
        # 集群认证信息有效情况（二种，SLZ 会拦截其他无效的情况）
        #   1. ca、cert、key 都有值
        #   2. token 有值
        auth_cfg_modified = bool((ca and cert and key) or token)
        exists_api_servers = cluster.api_servers.values_list("host", flat=True)
        api_servers_modified = set(exists_api_servers) != set(api_servers)

        # 只有在集群认证信息或 APIServers 有变更时，才需要检查集群是否可访问
        if (auth_cfg_modified or api_servers_modified) and not check_k8s_accessible(
            api_servers, ca=ca, cert=cert, key=key, token=token
        ):
            raise error_codes.CANNOT_UPDATE_CLUSTER.f(_("集群无法访问，请检查配置"))

        # 集群认证信息
        if auth_cfg_modified:
            cluster.ca_data = ca
            cluster.cert_data = cert
            cluster.key_data = key
            cluster.token_value = token

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
        # 更新时，如果密码为假值，则不更新
        cluster_es_cfg.password = es_cfg["password"] if es_cfg.get("password") else cluster_es_cfg.password

        with transaction.atomic(using="workloads"):
            cluster.save()
            cluster_es_cfg.save()

            if api_servers_modified:
                # 更新 ApiServers，采用先全部删除，再插入的方式
                cluster.api_servers.all().delete()
                APIServer.objects.bulk_create(
                    [APIServer(cluster=cluster, host=host, tenant_id=cluster.tenant_id) for host in api_servers]
                )

        # 更新集群后，需要根据变更的信息，决定是否刷新配置池
        if auth_cfg_modified or api_servers_modified:
            invalidate_global_configuration_pool()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="删除集群",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()

        # 删除集群前需要检查使用情况（分配策略，应用模块绑定等）
        state = ClusterAllocationGetter(cluster).get_state()
        if state.allocated_tenant_ids:
            raise error_codes.CANNOT_DELETE_CLUSTER.f(
                f"集群已被租户 {', '.join(state.allocated_tenant_ids)} 分配",
            )
        if state.bound_app_module_envs:
            raise error_codes.CANNOT_DELETE_CLUSTER.f(
                f"集群已被 {len(state.bound_app_module_envs)} 个应用部署环境绑定",
            )

        # TODO（多租户）删除集群是个危险操作，需要补充审计
        logger.warning(f"user {request.user.username} delete cluster {cluster_name}")

        ClusterElasticSearchConfig.objects.filter(cluster=cluster).delete()
        APIServer.objects.filter(cluster=cluster).delete()
        cluster.delete()

        # 删除集群后，需要刷新配置池
        invalidate_global_configuration_pool()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve_status(self, request, cluster_name, *args, **kwargs):
        """获取集群状态"""
        # FIXME: (多租户)提供集群基础信息，组件状态，集群特性配置完成度

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="获取集群默认特性",
        responses={status.HTTP_200_OK: ClusterDefaultFeatureFlagsRetrieveOutputSLZ()},
    )
    def retrieve_default_feature_flags(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()

        feature_flags = ClusterFeatureFlag.get_default_flags_by_cluster_type(cluster.type)
        # FIXME: (多租户)根据集群是否有安装某类组件，提供不同的默认特性配置（比如 GPA）

        return Response(ClusterDefaultFeatureFlagsRetrieveOutputSLZ({"feature_flags": feature_flags}).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="获取集群使用情况",
        responses={status.HTTP_200_OK: ClusterUsageRetrieveOutputSLZ()},
    )
    def retrieve_allocation_state(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()
        state = ClusterAllocationGetter(cluster).get_state()
        return Response(ClusterUsageRetrieveOutputSLZ(state).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="同步集群节点",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def sync_nodes(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()
        client = get_client_by_cluster_name(cluster_name=cluster.name)

        ignore_labels = {"node-role.kubernetes.io/master": "true"}
        state = generate_state(cluster.name, client, ignore_labels, cluster.tenant_id)
        sync_state_to_nodes(client, state)

        return Response(status=status.HTTP_204_NO_CONTENT)
