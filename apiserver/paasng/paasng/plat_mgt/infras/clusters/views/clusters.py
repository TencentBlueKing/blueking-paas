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
from typing import Any, Dict

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from requests.exceptions import RequestException
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.components import get_default_component_configs
from paas_wl.infras.cluster.constants import ClusterTokenType, ClusterType
from paas_wl.infras.cluster.models import (
    APIServer,
    Cluster,
    ClusterAppImageRegistry,
    ClusterComponent,
    ClusterElasticSearchConfig,
)
from paas_wl.infras.resources.base.base import get_client_by_cluster_name, invalidate_global_configuration_pool
from paas_wl.workloads.networking.egress.cluster_state import generate_state, sync_state_to_nodes
from paas_wl.workloads.networking.egress.models import RegionClusterState
from paas_wl.workloads.networking.entrance.constants import AddressType
from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.bcs.client import BCSClient
from paasng.infras.bcs.exceptions import BCSGatewayServiceError
from paasng.infras.bk_user.client import BkUserClient
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.infras.clusters.constants import HelmChartDeployStatus
from paasng.plat_mgt.infras.clusters.helm import HelmClient
from paasng.plat_mgt.infras.clusters.k8s import check_k8s_accessible
from paasng.plat_mgt.infras.clusters.serializers import (
    ClusterCreateInputSLZ,
    ClusterListOutputSLZ,
    ClusterNodesStateRetrieveOutputSLZ,
    ClusterNodesStateSyncRecordListOutputSLZ,
    ClusterRetrieveOutputSLZ,
    ClusterStatusRetrieveOutputSLZ,
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
            except (BCSGatewayServiceError, RequestException) as e:
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

        slz = ClusterCreateInputSLZ(data=request.data, context={"cur_tenant_id": cur_tenant_id})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        cert, ca, key, token = data["cert"], data["ca"], data["key"], data["token"]
        api_servers = data["api_servers"]

        # 检查集群是否可访问
        if not check_k8s_accessible(api_servers, ca, cert, key, token):
            raise error_codes.CANNOT_CREATE_CLUSTER.f(_("集群连通性测试失败，请检查 Server，Token 等配置是否准确"))

        with transaction.atomic(using="workloads"):
            # 创建集群
            cluster = Cluster.objects.create(
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
                    for cfg in get_default_component_configs()
                ]
            )

            # 创建 ElasticSearch 配置
            if es_cfg := data.get("elastic_search_config"):
                ClusterElasticSearchConfig.objects.create(cluster=cluster, tenant_id=cluster.tenant_id, **es_cfg)

            # 创建集群 App 镜像仓库配置
            if image_registry := data.get("app_image_registry"):
                ClusterAppImageRegistry.objects.create(cluster=cluster, tenant_id=cluster.tenant_id, **image_registry)

        # 新添加集群后，需要刷新配置池
        invalidate_global_configuration_pool()

        # 记录操作审计日志
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.CLUSTER,
            attribute=cluster.name,
            data_after=DataDetail(data=self.to_audit_data(cluster)),
        )

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="更新集群",
        request_body=ClusterUpdateInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()
        # 记录变更前的集群数据
        data_before = DataDetail(data=self.to_audit_data(cluster))

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
        # 注：通过 update 的方式，防止覆盖一些手动配置的注解 key
        cluster.annotations.update(data["annotations"])

        cert, ca, key, token = data["cert"], data["ca"], data["key"], data["token"]
        api_servers = data["api_servers"]

        # 检查集群认证信息 & APIServers 是否被修改
        auth_cfg_modified = not (
            ca == cluster.ca_data
            and cert == cluster.cert_data
            and key == cluster.key_data
            and token == cluster.token_value
        )
        exists_api_servers = cluster.api_servers.values_list("host", flat=True)
        api_servers_modified = set(exists_api_servers) != set(api_servers)

        # 只有在集群认证信息或 APIServers 有变更时，才需要检查集群是否可访问
        if (auth_cfg_modified or api_servers_modified) and not check_k8s_accessible(api_servers, ca, cert, key, token):
            raise error_codes.CANNOT_UPDATE_CLUSTER.f(_("集群连通性测试失败，请检查 Server，Token 等配置是否准确"))

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

        with transaction.atomic(using="workloads"):
            cluster.save()

            if api_servers_modified:
                # 更新 ApiServers，采用先全部删除再插入的方式
                cluster.api_servers.all().delete()
                APIServer.objects.bulk_create(
                    [APIServer(cluster=cluster, host=host, tenant_id=cluster.tenant_id) for host in api_servers]
                )

            # 集群 ElasticSearch 配置
            if es_cfg := data.get("elastic_search_config"):
                ClusterElasticSearchConfig.objects.update_or_create(
                    cluster=cluster, tenant_id=cluster.tenant_id, defaults=es_cfg
                )
            else:
                # es_cfg 为空意味走日志平台采集方案，不再需要保留 ClusterElasticSearchConfig
                ClusterElasticSearchConfig.objects.filter(cluster=cluster, tenant_id=cluster.tenant_id).delete()

            # 集群 App 镜像仓库配置
            if image_registry := data.get("app_image_registry"):
                ClusterAppImageRegistry.objects.update_or_create(
                    cluster=cluster, tenant_id=cluster.tenant_id, defaults=image_registry
                )
            else:
                # image_registry 为空意味着使用默认镜像仓库，不再需要保留 ClusterAppImageRegistry
                ClusterAppImageRegistry.objects.filter(cluster=cluster, tenant_id=cluster.tenant_id).delete()

        # 更新集群后，需要根据变更的信息，决定是否刷新配置池
        if auth_cfg_modified or api_servers_modified:
            invalidate_global_configuration_pool()

        # 记录操作审计日志
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.CLUSTER,
            attribute=cluster.name,
            data_before=data_before,
            data_after=DataDetail(data=self.to_audit_data(cluster)),
        )

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

        logger.warning(f"user {request.user.username} delete cluster {cluster_name}")

        # 记录操作审计日志
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.CLUSTER,
            attribute=cluster.name,
            data_after=DataDetail(data=self.to_audit_data(cluster)),
        )

        ClusterElasticSearchConfig.objects.filter(cluster=cluster).delete()
        ClusterAppImageRegistry.objects.filter(cluster=cluster).delete()
        APIServer.objects.filter(cluster=cluster).delete()
        cluster.delete()

        # 删除集群后，需要刷新配置池
        invalidate_global_configuration_pool()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="获取集群配置状态",
        responses={status.HTTP_200_OK: ClusterStatusRetrieveOutputSLZ()},
    )
    def retrieve_status(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()

        # 集群访问域名（子路径 / 子域名）是在集群配置（第二步）配置的，同属组件相关配置
        is_component_ready = bool(cluster.ingress_config.app_root_domains or cluster.ingress_config.sub_path_domains)
        # 只有通过上一步的检查，才去逐个检查必要组件的状态，避免低性能的获取 Helm Release Secrets 操作
        if is_component_ready:
            try:
                release_map = {r.chart.name: r for r in HelmClient(cluster_name).list_releases()}
            except Exception as e:
                logger.warning("list helm releases error: %s", e)
                is_component_ready = False
            else:
                for comp in ClusterComponent.objects.filter(cluster=cluster):
                    # 非必须组件，不影响集群状态
                    if not comp.required:
                        continue

                    rel = release_map.get(comp.name)
                    # 必要组件在集群中不存在，或者状态不是已安装，则认为集群组件为就绪
                    if not rel or rel.deploy_result.status != HelmChartDeployStatus.DEPLOYED:
                        is_component_ready = False
                        break

        state = {
            # 能够获取到集群的时候，基础配置已经是 OK 的
            # 注：创建/更新集群，都会检查集群的连通性，因此本 API 不做检查
            "basic": True,
            # 集群组件配置 & 集群组件状态
            "component": is_component_ready,
            # 集群特性配置（默认是空，如果不为空，则说明已配置）
            "feature": bool(cluster.feature_flags),
        }

        return Response(ClusterStatusRetrieveOutputSLZ(state).data)

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

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="获取集群节点信息",
        responses={status.HTTP_200_OK: ClusterNodesStateRetrieveOutputSLZ()},
    )
    def retrieve_nodes_state(self, request, cluster_name, *args, **kwargs):
        # 获取单条记录
        cluster_state = RegionClusterState.objects.filter(cluster_name=cluster_name).order_by("-created").first()
        if not cluster_state:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(ClusterNodesStateRetrieveOutputSLZ(instance=cluster_state).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster"],
        operation_description="获取节点同步记录",
        response={status.HTTP_200_OK: ClusterNodesStateSyncRecordListOutputSLZ()},
    )
    def retrieve_nodes_sync_records(self, request, cluster_name, *args, **kwargs):
        # 获取和传入的 cluster_name 相关的所有记录
        cluster_state = RegionClusterState.objects.filter(cluster_name=cluster_name).order_by("-created")

        return Response(ClusterNodesStateSyncRecordListOutputSLZ(cluster_state, many=True).data)

    @staticmethod
    def to_audit_data(cluster: Cluster) -> Dict[str, Any]:
        data = ClusterRetrieveOutputSLZ(cluster).data

        # 对特殊类型字段做转换，避免序列化时出错
        if es_cfg := data.get("elastic_search_config"):
            data["elastic_search_config"] = dict(es_cfg)

        if reg := data.get("app_image_registry"):
            data["app_image_registry"] = dict(reg)

        # List 类型的直接全部转换
        data["app_domains"] = [dict(d) for d in data["app_domains"]]

        return dict(data)
