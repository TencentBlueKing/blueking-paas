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
from typing import Tuple

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from pydantic import ValidationError as PDValidationError
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from semver import VersionInfo

from paas_wl.infras.cluster.models import Cluster, ClusterComponent
from paas_wl.utils.basic import to_error_string
from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.bcs.client import BCSUserClient
from paasng.infras.bcs.exceptions import BCSGatewayServiceError, HelmChartNotFound
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.infras.clusters.constants import ClusterComponentStatus
from paasng.plat_mgt.infras.clusters.helm import HelmClient
from paasng.plat_mgt.infras.clusters.k8s import K8SWorkloadStateGetter, ensure_k8s_namespace
from paasng.plat_mgt.infras.clusters.serializers import (
    ClusterComponentListOutputSLZ,
    ClusterComponentRetrieveOutputSLZ,
    ClusterComponentUpsertInputSLZ,
)
from paasng.plat_mgt.infras.clusters.serializers.components import ClusterComponentDiffVersionOutputSLZ
from paasng.plat_mgt.infras.clusters.values.constructors import get_values_constructor_cls
from paasng.plat_mgt.infras.clusters.values.getters import UserValuesGetter
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
        tags=["plat_mgt.infras.cluster_components"],
        operation_description="获取集群组件列表",
        responses={status.HTTP_200_OK: ClusterComponentListOutputSLZ(many=True)},
    )
    def list(self, request, cluster_name, *args, **kwargs):
        release_map = {r.chart.name: r for r in HelmClient(cluster_name).list_releases()}

        components = []
        for comp in self.get_queryset():
            # 从 helm release 中获取组件部署状态
            comp_status = ClusterComponentStatus.NOT_INSTALLED
            if rel := release_map.get(comp.name):
                comp_status = ClusterComponentStatus.from_helm_release_status(rel.deploy_result.status)

            components.append({"name": comp.name, "required": comp.required, "status": comp_status})

        return Response(data=ClusterComponentListOutputSLZ(components, many=True).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster_components"],
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

        try:
            values = UserValuesGetter(release).get()
        except PDValidationError:
            # 仅记录日志，不影响查询组件的其他信息 / 状态
            logger.exception("failed to get values for cluster %s component %s", cluster_name, component_name)
            # 如果获取简化后的 values 失败，则返回原始 values
            values = release.values

        component = {
            "chart": release.chart,
            "release": {
                "name": release.name,
                "namespace": release.namespace,
                "version": release.version,
                "deployed_at": release.deploy_result.created_at,
                "description": release.deploy_result.description,
                "status": release.deploy_result.status,
            },
            "values": values,
            "status": ClusterComponentStatus.from_helm_release_status(release.deploy_result.status),
            "workloads": K8SWorkloadStateGetter(cluster_name, release).get_states(),
        }
        return Response(data=ClusterComponentRetrieveOutputSLZ(component).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster_components"],
        operation_description="对比待更新组件版本",
        responses={status.HTTP_200_OK: ClusterComponentDiffVersionOutputSLZ()},
    )
    def diff_version(self, request, cluster_name, component_name, *args, **kwargs):
        cluster, component = self._get_cluster_and_component(cluster_name, component_name)
        cur_version, latest_version = self._get_component_cur_and_latest_version(request, cluster, component)
        resp_data = {"current_version": cur_version, "latest_version": latest_version}
        return Response(data=ClusterComponentDiffVersionOutputSLZ(resp_data).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster_components"],
        operation_description="更新或安装集群组件",
        request_body=ClusterComponentUpsertInputSLZ,
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def upsert(self, request, cluster_name, component_name, *args, **kwargs):
        cluster, component = self._get_cluster_and_component(cluster_name, component_name)
        cur_version, latest_version = self._get_component_cur_and_latest_version(request, cluster, component)

        if not (cluster.bcs_project_id and cluster.bcs_cluster_id):
            raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(_("非 BCS 集群需要手动更新组件"))

        if not latest_version:
            raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(_("无法获取组件最新版本信息"))

        # 如果目前集群中已经有部署的版本，则检查是否为跨大版本更新
        if cur_version:
            try:
                cur_ver_info = VersionInfo.parse(cur_version)
                latest_ver_info = VersionInfo.parse(latest_version)
            except (TypeError, ValueError):
                raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(_("版本号解析异常"))

            if cur_ver_info.major != latest_ver_info.major:
                raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(_("不支持跨大版本更新，需要到集群中手动操作"))

        # 组件配置校验
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

        # 记录变更前的组件数据
        data_before = DataDetail(
            data={
                "version": cur_version,
                "values": release.values if release else None,
            }
        )

        # 确保命名空间一定存在
        ensure_k8s_namespace(cluster_name, namespace)

        # 基于用户提交的 values，构造最终的 values
        try:
            values_constructor = get_values_constructor_cls(component_name)(cluster)
            values = values_constructor.construct(data["values"])
        except PDValidationError as e:
            raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(to_error_string(e))
        except Exception:
            logger.exception("failed to construct values for cluster %s component %s", cluster_name, component_name)
            raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(_("配置异常，请联系管理员处理"))

        # 调用 BCS API 下发组件（Helm Chart)
        bcs_client = BCSUserClient(
            get_tenant(request.user).id,
            request.user.username,
            request.COOKIES.get(settings.BK_COOKIE_NAME),
        )
        try:
            # bcs upgrade 接口默认带上 --install 参数，因此调用时无需区分是新建还是更新
            bcs_client.upgrade_release(
                cluster.bcs_project_id,
                cluster.bcs_cluster_id,
                namespace,
                release_name,
                component.repository,
                component_name,
                latest_version,
                values,
            )
        except HelmChartNotFound as e:
            raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(str(e))
        except BCSGatewayServiceError as e:
            logger.exception("failed to upgrade cluster %s component %s", cluster_name, component_name)
            raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(str(e))

        # 添加操作审计记录
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.CLUSTER,
            data_before=data_before,
            data_after=DataDetail(
                data={"version": latest_version, "values": values},
            ),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _get_cluster_and_component(cluster_name, component_name) -> Tuple[Cluster, ClusterComponent]:
        """获取集群和组件对象"""
        # FIXME:（多租户）有租户管理员后，得控制用户可访问的集群权限（也许得抽个 mixin？）
        cluster = Cluster.objects.filter(name=cluster_name).first()
        if not cluster:
            raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(_("指定集群不存在"))

        component = ClusterComponent.objects.filter(cluster=cluster, name=component_name).first()
        if not component:
            raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(_("指定集群组件不存在"))

        return cluster, component

    @staticmethod
    def _get_component_cur_and_latest_version(
        request, cluster: Cluster, component: ClusterComponent
    ) -> Tuple[str | None, str | None]:
        """获取组件在集群中的当前版本 & 可选的最新版本"""
        cur_version, latest_version = None, None
        if release := HelmClient(cluster.name).get_release(component.name):
            cur_version = release.chart.version

        # 非 BCS 集群无法获取组件版本信息
        if not (cluster.bcs_project_id and cluster.bcs_cluster_id):
            return cur_version, latest_version

        bcs_client = BCSUserClient(
            get_tenant(request.user).id,
            request.user.username,
            request.COOKIES.get(settings.BK_COOKIE_NAME),
        )
        try:
            chart_versions = bcs_client.get_chart_versions(
                cluster.bcs_project_id, component.repository, component.name
            )
        except BCSGatewayServiceError:
            raise error_codes.CANNOT_UPSERT_CLUSTER_COMPONENT.f(_("获取组件版本信息失败，请确认操作人是否有权限"))

        if chart_versions:
            # API 返回是按时间逆序，因此第一个就是最新版本
            latest_version = chart_versions[0].version

        return cur_version, latest_version
