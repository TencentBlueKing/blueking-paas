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
from collections import Counter

from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.accessories.publish.market.models import Product
from paasng.core.core.storages.redisdb import DefaultRediStore
from paasng.core.tenant.constants import AppTenantMode
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.bkmonitorv3.exceptions import BkMonitorApiError, BkMonitorGatewayServiceError
from paasng.infras.bkmonitorv3.shim import update_or_create_bk_monitor_space
from paasng.infras.iam.helpers import fetch_role_members
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.applications import serializers as slzs
from paasng.plat_mgt.applications.utils.filters import ApplicationFilterBackend
from paasng.plat_mgt.bk_plugins.views import is_plugin_instance_exist, is_user_plugin_admin
from paasng.platform.applications.constants import ApplicationRole, ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.applications.tasks import cal_app_resource_quotas

logger = logging.getLogger(__name__)


class ApplicationListViewSet(viewsets.GenericViewSet):
    """平台管理 - 应用列表 API"""

    queryset = Application.objects.all()
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]
    filter_backends = [ApplicationFilterBackend]
    pagination_class = LimitOffsetPagination

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用列表",
        responses={status.HTTP_200_OK: slzs.ApplicationListOutputSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取应用列表"""
        queryset = self.get_queryset()
        filter_queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(filter_queryset)
        app_resource_quotas = self.get_app_resource_quotas()

        slz = slzs.ApplicationListOutputSLZ(
            page,
            many=True,
            context={"request": request, "app_resource_quotas": app_resource_quotas},
        )
        return self.get_paginated_response(slz.data)

    def get_app_resource_quotas(self) -> dict:
        """获取应用资源配额信息，优先从 Redis 缓存获取，缺失时触发异步任务计算"""
        # 尝试从 Redis 中获取资源配额
        store = DefaultRediStore(rkey="quotas::app")
        app_resource_quotas = store.get()

        if not app_resource_quotas:
            # 触发异步任务计算资源配额
            # 计算完成后会将结果存入 Redis 中
            cal_app_resource_quotas.delay()

        return app_resource_quotas or {}

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取各租户的应用数量",
        responses={status.HTTP_200_OK: slzs.TenantAppStatisticsOutputSLZ(many=True)},
    )
    def list_tenant_app_statistics(self, request):
        """获取各租户的应用数量"""
        # 应用所有过滤条件, 获取过滤后的查询集
        filtered_queryset = self.filter_queryset(self.get_queryset())

        tenant_id_list = []
        # 查询各个租户的应用数量
        tenant_ids = filtered_queryset.values_list("tenant_id", flat=True)
        tenant_id_counts = Counter(tenant_ids)
        for tenant_id in sorted(tenant_id_counts.keys()):
            tenant_id_list.append({"tenant_id": tenant_id, "app_count": tenant_id_counts[tenant_id]})
        slz = slzs.TenantAppStatisticsOutputSLZ(tenant_id_list, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用租户模式类型列表",
        responses={status.HTTP_200_OK: slzs.TenantModeListOutputSLZ(many=True)},
    )
    def list_tenant_modes(self, request, *args, **kwargs):
        """获取应用租户模式类型列表"""
        tenant_modes = [{"type": type, "label": label} for type, label in AppTenantMode.get_choices()]
        slz = slzs.TenantModeListOutputSLZ(tenant_modes, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用类型列表",
        responses={status.HTTP_200_OK: slzs.ApplicationTypeOutputSLZ(many=True)},
    )
    def list_app_types(self, request):
        """获取应用类型列表"""
        app_types = [{"type": type, "label": label} for type, label in ApplicationType.get_choices()]
        slz = slzs.ApplicationTypeOutputSLZ(app_types, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)


class ApplicationDetailViewSet(viewsets.GenericViewSet):
    """平台管理 - 应用详情 API"""

    queryset = Application.objects.all()
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用详情",
        responses={status.HTTP_200_OK: slzs.ApplicationDetailOutputSLZ()},
    )
    def retrieve(self, request, app_code):
        """获取应用详情"""
        application = get_object_or_404(self.get_queryset(), code=app_code)

        # 获取应用管理员信息和插件管理信息
        user_is_admin_in_app = self.request.user.username in fetch_role_members(
            application.code, ApplicationRole.ADMINISTRATOR
        )

        # 判断是否为插件应用且插件实例存在
        is_plugin_with_instance = application.is_plugin_app and is_plugin_instance_exist(application.code)

        app_admin = {
            "user_is_admin_in_app": user_is_admin_in_app,
            "show_plugin_admin_operations": is_plugin_with_instance,
            "user_is_admin_in_plugin": (
                is_user_plugin_admin(request.user.username, application.code) if is_plugin_with_instance else None
            ),
        }

        slz = slzs.ApplicationDetailOutputSLZ(
            {
                "basic_info": application,
                "app_admin": app_admin,
                "modules_info": application.modules.all(),
            }
        )
        return Response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="更新应用名称",
        request_body=slzs.ApplicationNameUpdateInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update_app_name(self, request, app_code):
        """更新应用名称"""
        application = get_object_or_404(self.get_queryset(), code=app_code)

        data_before = DataDetail(
            data={
                "name": application.name,
                "name_en": application.name_en,
            },
        )

        slz = slzs.ApplicationNameUpdateInputSLZ(data=request.data, instance=application)
        slz.is_valid(raise_exception=True)
        application = slz.save()

        Product.objects.filter(code=app_code).update(name_zh_cn=application.name, name_en=application.name_en)

        # 修改应用在蓝鲸监控命名空间的名称
        # 蓝鲸监控查询、更新一个不存在的应用返回的 code 都是 500，没有具体的错误码来标识是不是应用不存在，故直接调用更新API，忽略错误信息
        try:
            update_or_create_bk_monitor_space(application)
        except (BkMonitorGatewayServiceError, BkMonitorApiError) as e:
            logger.info(f"Failed to update app space on BK Monitor, {e}")
        except Exception:
            logger.exception("Failed to update app space on BK Monitor (unknown error)")

        data_after = DataDetail(
            data={
                "name": application.name,
                "name_en": application.name_en,
            },
        )

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY_BASIC_INFO,
            target=OperationTarget.APP,
            app_code=application.code,
            data_before=data_before,
            data_after=data_after,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="更新应用集群",
        request_body=slzs.UpdateClusterSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update_cluster(self, request, app_code, module_name, env_name):
        """更新应用集群"""

        application = get_object_or_404(self.get_queryset(), code=app_code)
        module = application.get_module(module_name)
        env = get_object_or_404(module.envs, environment=env_name)

        slz = slzs.UpdateClusterSLZ(
            data=request.data,
            context={"user": request.user, "environment": env.environment, "region": application.region},
        )
        slz.is_valid(raise_exception=True)

        cluster_name = slz.validated_data["name"]
        cluster = get_object_or_404(Cluster, name=cluster_name)

        data_before = DataDetail(data={"cluster": env.wl_app.latest_config.cluster})

        EnvClusterService(env).bind_cluster(cluster.name)

        data_after = DataDetail(data={"cluster": cluster.name})

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.CLUSTER,
            app_code=application.code,
            data_before=data_before,
            data_after=data_after,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
