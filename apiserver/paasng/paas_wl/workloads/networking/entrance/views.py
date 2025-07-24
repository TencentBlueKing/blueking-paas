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

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.workloads.networking.entrance import serializers as slzs
from paas_wl.workloads.networking.entrance.serializers import DomainForUpdateSLZ, DomainSLZ, validate_domain_payload
from paas_wl.workloads.networking.ingress.domains.manager import get_custom_domain_mgr
from paas_wl.workloads.networking.ingress.models import Domain
from paasng.infras.accounts.models import User
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.accounts.permissions.user import user_can_operate_in_region
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.api_docs import openapi_empty_response
from paasng.utils.error_codes import error_codes

from .entrance import get_entrances

logger = logging.getLogger(__name__)


class AppDomainsViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """管理应用独立域名的 ViewSet"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    lookup_url_kwarg = "id"
    lookup_field = "pk"

    def get_queryset(self) -> QuerySet:
        """Get Domain QuerySet of current application"""
        application = self.get_application()
        module_ids = list(application.modules.values_list("id", flat=True))
        return Domain.objects.filter(module_id__in=module_ids)

    @swagger_auto_schema(operation_id="list-app-domains", response_serializer=DomainSLZ(many=True), tags=["Domains"])
    def list(self, request, **kwargs):
        """查看应用的所有自定义域名信息

        结果默认按（“模块名”、“环境”）排序
        """
        # Get results and sort
        domains = self.get_queryset()
        domains = sorted(domains, key=lambda d: (d.module.name, d.environment.environment, d.id))

        serializer = DomainSLZ(domains, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_id="create-app-domain",
        request_body=DomainSLZ,
        response_serializer=DomainSLZ,
        tags=["Domains"],
    )
    def create(self, request, **kwargs):
        """创建一个独立域名

        - 注意 `path` 字段目前支持多级子路径（如 '/foo/bar/'）
        - 【客户端】建议使用文档里的正则进行校验
        - 【客户端】`https_enabled` 暂不暴露给给用户
        """
        application = self.get_application()
        if not self.allow_modifications(request.user, application.region):
            raise error_codes.CREATE_CUSTOM_DOMAIN_FAILED.format(
                "当前应用版本不允许手动管理独立域名，请联系平台管理员"
            )

        data = validate_domain_payload(request.data, application, serializer_cls=DomainSLZ)
        env = application.get_module(data["module"]["name"]).get_envs(data["environment"]["environment"])
        domain = get_custom_domain_mgr(application).create(
            env=env,
            host=data["name"],
            path_prefix=data["path_prefix"],
            https_enabled=data["https_enabled"],
        )

        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE,
            target=OperationTarget.APP_DOMAIN,
            module_name=env.module.name,
            environment=env.environment,
            data_after=DataDetail(data=DomainSLZ(domain).data),
        )
        return Response(DomainSLZ(domain).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_id="update-app-domain",
        request_body=DomainForUpdateSLZ,
        response_serializer=DomainSLZ,
        tags=["Domains"],
    )
    def update(self, request, **kwargs):
        """更新一个独立域名的域名与路径信息"""
        application = self.get_application()
        domain = get_object_or_404(self.get_queryset(), pk=self.kwargs["id"])
        if not self.allow_modifications(request.user, application.region):
            raise error_codes.UPDATE_CUSTOM_DOMAIN_FAILED.format(
                "当前应用版本不允许手动管理独立域名，请联系平台管理员"
            )

        data_before = DataDetail(data=DomainSLZ(domain).data)
        data = validate_domain_payload(request.data, application, serializer_cls=DomainForUpdateSLZ, instance=domain)
        new_domain = get_custom_domain_mgr(application).update(
            domain, host=data["name"], path_prefix=data["path_prefix"], https_enabled=data["https_enabled"]
        )

        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.APP_DOMAIN,
            module_name=domain.module.name,
            environment=domain.environment.environment,
            data_before=data_before,
            data_after=DataDetail(data=DomainSLZ(new_domain).data),
        )
        return Response(DomainSLZ(new_domain).data)

    @swagger_auto_schema(operation_id="delete-app-domain", responses={204: openapi_empty_response}, tags=["Domains"])
    def destroy(self, request, *args, **kwargs):
        """通过 ID 删除一个独立域名"""
        application = self.get_application()
        domain = get_object_or_404(self.get_queryset(), pk=self.kwargs["id"])
        if not self.allow_modifications(request.user, application.region):
            raise error_codes.DELETE_CUSTOM_DOMAIN_FAILED.format(
                "当前应用版本不允许手动管理独立域名，请联系平台管理员"
            )

        data_before = DataDetail(data=DomainSLZ(domain).data)
        get_custom_domain_mgr(application).delete(domain)

        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.DELETE,
            target=OperationTarget.APP_DOMAIN,
            module_name=domain.module.name,
            environment=domain.environment.environment,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(response_serializer=slzs.CustomDomainsConfigSLZ(many=True), tags=["访问入口"])
    def list_configs(self, request, code):
        """查看独立域名相关配置信息，比如前端负载均衡 IP 地址等"""
        application = self.get_application()
        results = []
        for module in application.modules.all():
            for env in module.envs.all():
                cluster = EnvClusterService(env).get_cluster()
                # `cluster` could be None when application's engine was disabled
                frontend_ingress_ip = cluster.ingress_config.frontend_ingress_ip if cluster else ""
                results.append(
                    {
                        "module": module.name,
                        "environment": env.environment,
                        "frontend_ingress_ip": frontend_ingress_ip,
                    }
                )
        return Response(slzs.CustomDomainsConfigSLZ(results, many=True).data)

    @staticmethod
    def allow_modifications(user: User, region: str) -> bool:
        """Whether modifying custom_domain is allowed"""
        return user_can_operate_in_region(user, region)


class AppEntranceViewSet(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(response_serializer=slzs.ModuleEntrancesSLZ(many=True), tags=["访问入口"])
    def list_all_entrances(self, request, code):
        """查看应用所有模块的访问入口"""
        application = self.get_application()
        all_entrances = get_entrances(application)
        return Response(data=slzs.ModuleEntrancesSLZ(all_entrances, many=True).data)
