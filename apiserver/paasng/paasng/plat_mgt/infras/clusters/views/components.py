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
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from pydantic import ValidationError as PDValidationError
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.models import Cluster, ClusterComponent
from paas_wl.utils.basic import to_error_string
from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.bcs.client import BCSUserClient
from paasng.infras.bcs.exceptions import BCSGatewayServiceError, HelmChartNotFound
from paasng.plat_mgt.infras.clusters.constants import ClusterComponentStatus
from paasng.plat_mgt.infras.clusters.helm import HelmClient
from paasng.plat_mgt.infras.clusters.k8s import K8SWorkloadStateGetter
from paasng.plat_mgt.infras.clusters.serializers import (
    ClusterComponentListOutputSLZ,
    ClusterComponentRetrieveOutputSLZ,
    ClusterComponentUpsertInputSLZ,
)
from paasng.plat_mgt.infras.clusters.serializers.components import ClusterComponentDiffVersionOutputSLZ
from paasng.plat_mgt.infras.clusters.values.constructors import get_values_constructor_cls
from paasng.plat_mgt.infras.clusters.values.getters import get_values_getter_cls
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class ClusterComponentViewSet(viewsets.GenericViewSet):
    """集群组件管理"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def get_queryset(self):
        # FIXME：（多租户）根据平台/租户管理员身份，返回不同的集群组件列表
        # 必要组件排前面，然后按照字母序排序
        return ClusterComponent.objects.filter(
            cluster__name=self.kwargs["cluster_name"],
        ).order_by("-required", "name")

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster_components"],
        operation_description="获取集群组件列表",
        responses={status.HTTP_200_OK: ClusterComponentListOutputSLZ(many=True)},
    )
    def list(self, request, cluster_name, *args, **kwargs):
        release_map = {r.name: r for r in HelmClient(cluster_name).list_releases()}

        components = []
        for comp in self.get_queryset():
            # 从 helm release 中获取组件部署状态
            status = ClusterComponentStatus.NOT_INSTALLED
            if rel := release_map.get(comp.name):
                status = ClusterComponentStatus.from_helm_release_status(rel.deploy_result.status)

            components.append({"name": comp.name, "required": comp.required, "status": status})

        return Response(data=ClusterComponentListOutputSLZ(components, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster_components"],
        operation_description="获取集群组件详情",
        responses={status.HTTP_200_OK: ClusterComponentRetrieveOutputSLZ()},
    )
    def retrieve(self, request, cluster_name, component_name, *args, **kwargs):
        # FIXME:（多租户）有租户管理员后，得控制用户可访问的集群权限（也许得抽个 mixin？）
        if not Cluster.objects.filter(name=cluster_name).first():
            return Response(status=status.HTTP_404_NOT_FOUND)

        release = HelmClient(cluster_name).get_release(component_name)
        if not release:
            return Response(status=status.HTTP_404_NOT_FOUND)

        workload_states = K8SWorkloadStateGetter(cluster_name, release).get_states()
        values_getter = get_values_getter_cls(component_name)(release)

        try:
            values = values_getter.get()
        except PDValidationError:
            # 仅记录日志，不影响查询组件的其他信息 / 状态
            logger.exception("failed to get values for cluster %s component %s", cluster_name, component_name)
            # 如果获取简化后的 values 失败，则返回原始 values
            values = values_getter.raw()

        component = {
            "chart": release.chart,
            "release": {
                "name": release.name,
                "namespace": release.namespace,
                "created_at": release.deploy_result.created_at,
                "description": release.deploy_result.description,
                "status": release.deploy_result.status,
            },
            "values": values,
            "workloads": workload_states,
        }
        return Response(data=ClusterComponentRetrieveOutputSLZ(component).data)

    def diff_version(self, request, cluster_name, component_name, *args, **kwargs):
        # FIXME:（多租户）有租户管理员后，得控制用户可访问的集群权限（也许得抽个 mixin？）
        cluster = Cluster.objects.filter(name=cluster_name).first()
        if not cluster:
            return Response(status=status.HTTP_404_NOT_FOUND)

        cur_version, latest_version = None, None
        if release := HelmClient(cluster_name).get_release(component_name):
            cur_version = release.version

        bcs_client = BCSUserClient(
            get_tenant(request.user).id, request.user.username, request.COOKIES.get(settings.BK_COOKIE_NAME)
        )
        if chart_versions := bcs_client.get_chart_versions(
            cluster.bcs_project_id, settings.CLUSTER_COMPONENT_HELM_REPO, component_name
        ):
            # API 返回是按时间逆序，因此第一个就是最新版本
            latest_version = chart_versions[0].version

        resp_data = {"current_version": cur_version, "latest_version": latest_version}
        return Response(data=ClusterComponentDiffVersionOutputSLZ(resp_data).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster_components"],
        operation_description="更新或新建集群组件",
        request_body=ClusterComponentUpsertInputSLZ,
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def upsert(self, request, cluster_name, component_name, *args, **kwargs):
        # FIXME:（多租户）有租户管理员后，得控制用户可访问的集群权限（也许得抽个 mixin？）
        cluster = Cluster.objects.filter(name=cluster_name).first()
        if not cluster:
            return Response(status=status.HTTP_404_NOT_FOUND)

        slz = ClusterComponentUpsertInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        # 默认使用集群推荐的命名空间
        namespace = cluster.component_preferred_namespace
        # 默认使用组件名称作为 release 名称
        release_name = component_name
        if release := HelmClient(cluster_name).get_release(component_name):
            # 如果组件已经部署
            # 1. 需要指定成对应的命名空间镜像更新
            namespace = release.namespace
            # 2. 需要使用已有的 release 名称
            release_name = release.name

        # 基于用户提交的 values，构造最终的 values
        values_constructor = get_values_constructor_cls(component_name)(cluster)
        try:
            values = values_constructor.construct(data["values"])
        except PDValidationError as e:
            raise error_codes.CANNOT_UPDATE_CLUSTER_COMPONENT.f(to_error_string(e))
        except Exception:
            logger.exception("failed to construct values for cluster %s component %s", cluster_name, component_name)
            raise error_codes.CANNOT_UPDATE_CLUSTER_COMPONENT.f(_("配置异常，请联系管理员处理"))

        # 调用 BCS API 下发组件（Helm Chart)
        bcs_client = BCSUserClient(
            get_tenant(request.user).id,
            request.user.username,
            request.COOKIES.get(settings.BK_COOKIE_NAME),
        )
        try:
            # bcs upgrade 接口默认带上 --install 参数，因此调用时无需区分是新建还是更新
            bcs_client.upgrade_release_with_latest_chart_version(
                cluster.bcs_project_id,
                cluster.bcs_cluster_id,
                namespace,
                release_name,
                settings.CLUSTER_COMPONENT_HELM_REPO,
                component_name,
                values,
            )
        except HelmChartNotFound as e:
            raise error_codes.CANNOT_UPDATE_CLUSTER_COMPONENT.f(str(e))
        except BCSGatewayServiceError as e:
            logger.exception("failed to upgrade cluster %s component %s", cluster_name, component_name)
            raise error_codes.CANNOT_UPDATE_CLUSTER_COMPONENT.f(str(e))

        return Response(status=status.HTTP_204_NO_CONTENT)
