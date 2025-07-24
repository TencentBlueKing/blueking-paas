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

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.workloads.networking.entrance.serializers import DomainForUpdateSLZ, DomainSLZ, validate_domain_payload
from paas_wl.workloads.networking.ingress.domains.manager import get_custom_domain_mgr
from paas_wl.workloads.networking.ingress.models import Domain
from paasng.infras.accounts.permissions.global_site import SiteAction, site_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.platform.applications.models import Application
from paasng.utils.api_docs import openapi_empty_response


class AppDomainsViewSet(GenericViewSet):
    """管理应用独立域名的 ViewSet"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_queryset(self, application: Application) -> QuerySet:
        """Get Domain QuerySet of current application"""
        module_ids = list(application.modules.values_list("id", flat=True))
        return Domain.objects.filter(module_id__in=module_ids)

    @swagger_auto_schema(operation_id="list-app-domains", response_serializer=DomainSLZ(many=True), tags=["Domains"])
    def list(self, request, **kwargs):
        """查看应用的所有自定义域名信息

        结果默认按（“模块名”、“环境”）排序
        """
        application = get_object_or_404(Application, code=kwargs["code"])

        # Get results and sort
        domains = self.get_queryset(application)
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
        - 【客户端】模块与环境建议使用下拉框
        - 【客户端】`https_enabled` 暂不暴露给给用户
        """
        application = get_object_or_404(Application, code=kwargs["code"])

        data = validate_domain_payload(request.data, application, serializer_cls=DomainSLZ)
        env = application.get_module(data["module"]["name"]).get_envs(data["environment"]["environment"])
        domain = get_custom_domain_mgr(application).create(
            env=env,
            host=data["name"],
            path_prefix=data["path_prefix"],
            https_enabled=data["https_enabled"],
        )

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.APP_DOMAIN,
            app_code=application.code,
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
        application = get_object_or_404(Application, code=kwargs["code"])
        domain = get_object_or_404(self.get_queryset(application), pk=self.kwargs["id"])
        data_before = DataDetail(data=DomainSLZ(domain).data)

        data = validate_domain_payload(request.data, application, instance=domain, serializer_cls=DomainForUpdateSLZ)
        new_domain = get_custom_domain_mgr(application).update(
            domain, host=data["name"], path_prefix=data["path_prefix"], https_enabled=data["https_enabled"]
        )

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.APP_DOMAIN,
            app_code=application.code,
            module_name=domain.module.name,
            environment=domain.environment.environment,
            data_before=data_before,
            data_after=DataDetail(data=DomainSLZ(new_domain).data),
        )
        return Response(DomainSLZ(new_domain).data)

    @swagger_auto_schema(operation_id="delete-app-domain", responses={204: openapi_empty_response}, tags=["Domains"])
    def destroy(self, request, *args, **kwargs):
        """通过 ID 删除一个独立域名"""
        application = get_object_or_404(Application, code=kwargs["code"])
        domain = get_object_or_404(self.get_queryset(application), pk=self.kwargs["id"])
        data_before = DataDetail(data=DomainSLZ(domain).data)

        get_custom_domain_mgr(application).delete(domain)

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.APP_DOMAIN,
            app_code=application.code,
            module_name=domain.module.name,
            environment=domain.environment.environment,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
