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
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.accessories.publish.market.models import ApplicationExtraInfo, Product, Tag
from paasng.accessories.publish.sync_market.utils import cascade_delete_legacy_app
from paasng.core.tenant.constants import AppTenantMode
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.bkmonitorv3.exceptions import BkMonitorApiError, BkMonitorGatewayServiceError
from paasng.infras.bkmonitorv3.shim import update_or_create_bk_monitor_space
from paasng.infras.iam.helpers import delete_builtin_user_groups, delete_grade_manager, fetch_role_members
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.applications import serializers as slzs
from paasng.plat_mgt.applications.utils.filters import ApplicationFilterBackend
from paasng.plat_mgt.bk_plugins.views import is_plugin_instance_exist, is_user_plugin_admin
from paasng.platform.applications.constants import ApplicationRole, ApplicationType
from paasng.platform.applications.models import Application
from paasng.utils.error_codes import error_codes

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

        slz = slzs.ApplicationListOutputSLZ(page, many=True)
        return self.get_paginated_response(slz.data)

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
                is_user_plugin_admin(application.code, request.user.username) if is_plugin_with_instance else None
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
        data = slz.validated_data
        # 仅修改对应语言的应用名称, 如果前端允许同时填写中英文的应用名称, 则可以去掉该逻辑.
        if get_language() == "zh-cn":
            application.name = data["name_zh_cn"]
        elif get_language() == "en":
            application.name_en = data["name_en"]
        application.save(update_fields=["name", "name_en"])

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
        operation_description="更新应用分类",
        request_body=slzs.ApplicationCategoryUpdateInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update_app_category(self, request, app_code):
        application = get_object_or_404(self.get_queryset(), code=app_code)

        try:
            extra_info = ApplicationExtraInfo.objects.get(application=application)
            current_tag_name = extra_info.tag.name if extra_info and extra_info.tag else None
        except ApplicationExtraInfo.DoesNotExist:
            extra_info = None
            current_tag_name = None

        data_before = DataDetail(data={"category": current_tag_name})

        slz = slzs.ApplicationCategoryUpdateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        category = data["category"]
        tag = Tag.objects.get(pk=category)

        # 更新应用分类
        ApplicationExtraInfo.objects.update_or_create(
            application=application,
            defaults={
                "tag": tag,
                "tenant_id": application.tenant_id,
            },
        )

        data_after = DataDetail(data={"category": tag.name})

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
        request_body=slzs.ApplicationBindClusterUpdateInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update_cluster(self, request, app_code, module_name, env_name):
        """更新应用集群"""

        application = get_object_or_404(self.get_queryset(), code=app_code)
        module = application.get_module(module_name)
        env = get_object_or_404(module.envs, environment=env_name)

        slz = slzs.ApplicationBindClusterUpdateInputSLZ(
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


class DeletedApplicationViewSet(viewsets.GenericViewSet):
    """平台管理 - 删除应用 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]
    filter_backends = [ApplicationFilterBackend]
    pagination_class = LimitOffsetPagination

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取软删除应用列表",
        responses={status.HTTP_200_OK: slzs.DeletedApplicationListOutputSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取软删除应用列表"""
        deleted_apps = Application.default_objects.filter(is_deleted=True)
        filter_queryset = self.filter_queryset(deleted_apps)

        page = self.paginate_queryset(filter_queryset)

        slz = slzs.DeletedApplicationListOutputSLZ(page, many=True)
        return self.get_paginated_response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="彻底删除应用",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, app_code):
        """彻底删除应用"""
        try:
            to_del_app = Application.default_objects.get(code=app_code, is_deleted=True)
        except Application.DoesNotExist:
            raise error_codes.APP_NOT_FOUND.f(_("应用不存在或未被软删除"))

        # 从 PaaS 2.0 中删除相关信息
        try:
            cascade_delete_legacy_app("code", app_code, False)
        except Exception:
            logger.exception("Failed to delete application %s from PaaS2.0", app_code)
            raise error_codes.CANNOT_HARD_DELETE_APP.f(_("PaaS 2.0 中信息删除失败"))

        # 删除权限中心相关数据
        delete_builtin_user_groups(app_code)
        delete_grade_manager(app_code)

        # 从 PaaS 3.0 中删除相关信息
        to_del_app.hard_delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
