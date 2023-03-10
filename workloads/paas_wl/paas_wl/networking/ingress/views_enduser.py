# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.networking.ingress.config import get_custom_domain_config
from paas_wl.networking.ingress.domains.manager import get_custom_domain_mgr, validate_domain_payload
from paas_wl.networking.ingress.entities.service import service_kmodel
from paas_wl.networking.ingress.managers.misc import AppDefaultIngresses, LegacyAppIngressMgr
from paas_wl.networking.ingress.models import Domain
from paas_wl.networking.ingress.serializers import DomainForUpdateSLZ, DomainSLZ, ProcIngressSLZ, ProcServiceSLZ
from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.error_codes import error_codes
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.views import ApplicationCodeInPathMixin
from paasng.utils.api_docs import openapi_empty_response

logger = logging.getLogger(__name__)


class ProcessServicesViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """管理应用内部服务相关 API"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def list(self, request, code, module_name, environment):
        """查看所有进程服务信息"""
        env = self.get_env_via_path()
        wl_app = WlApp.objects.get(pk=env.engine_app_id)
        # Get all services
        proc_services = service_kmodel.list_by_app(wl_app)
        proc_services_json = ProcServiceSLZ(proc_services, many=True).data

        # Get default ingress
        try:
            ingress_obj = LegacyAppIngressMgr(wl_app).get()
            default_ingress_json = ProcIngressSLZ(ingress_obj).data
        except AppEntityNotFound:
            default_ingress_json = None

        return Response({'default_ingress': default_ingress_json, 'proc_services': proc_services_json})

    def update(self, request, code, module_name, environment, service_name):
        """更新某个服务下的端口配置信息"""
        env = self.get_env_via_path()
        wl_app = WlApp.objects.get(pk=env.engine_app_id)
        serializer = ProcServiceSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            proc_service = service_kmodel.get(wl_app, service_name)
        except AppEntityNotFound:
            raise error_codes.ERROR_UPDATING_PROC_SERVICE.f('未找到服务')

        proc_service.ports = serializer.validated_data["ports"]
        service_kmodel.update(proc_service)
        return Response(ProcServiceSLZ(proc_service).data)


class ProcessIngressesViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """管理应用模块主入口相关 API"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def update(self, request, code, module_name, environment):
        """更改模块各环境主入口"""
        env = self.get_env_via_path()
        wl_app = WlApp.objects.get(pk=env.engine_app_id)

        serializer = ProcIngressSLZ(data=request.data, context={'app': wl_app})
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        # 更新默认域名
        try:
            ret = AppDefaultIngresses(wl_app).safe_update_target(data['service_name'], data['service_port_name'])
        except Exception:
            logger.exception('unable to update ingresses from view')
            raise error_codes.ERROR_UPDATING_PROC_INGRESS.f('请稍候重试')
        if ret.num_of_successful == 0:
            raise error_codes.ERROR_UPDATING_PROC_INGRESS.f('未找到任何访问入口')

        # Return the legacy default ingress data for compatibility reason
        serializer = ProcIngressSLZ(LegacyAppIngressMgr(wl_app).get())
        return Response(serializer.data)


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

    @swagger_auto_schema(operation_id="list-app-domains", response_serializer=DomainSLZ(many=True), tags=['Domains'])
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
        tags=['Domains'],
    )
    def create(self, request, **kwargs):
        """创建一个独立域名

        - 注意 `path` 字段目前只支持一级子路径，多级子路径（如 '/foo/bar/'）暂不支持
        - 【客户端】建议使用文档里的正则进行校验
        - 【客户端】模块与环境建议使用下拉框
        - 【客户端】`https_enabled` 暂不暴露给给用户
        """
        application = self.get_application()
        if not self.allow_modifications(application.region):
            raise error_codes.CREATE_CUSTOM_DOMAIN_FAILED.format('当前应用版本不允许手动管理独立域名，请联系平台管理员')

        data = validate_domain_payload(request.data, application, serializer_cls=DomainSLZ)
        env = application.get_module(data["module"]["name"]).get_envs(data["environment"]["environment"])
        instance = get_custom_domain_mgr(application).create(
            env=env,
            host=data["name"],
            path_prefix=data["path_prefix"],
            https_enabled=data["https_enabled"],
        )
        return Response(DomainSLZ(instance).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_id="update-app-domain",
        request_body=DomainForUpdateSLZ,
        response_serializer=DomainSLZ,
        tags=['Domains'],
    )
    def update(self, request, **kwargs):
        """更新一个独立域名的域名与路径信息"""
        application = self.get_application()
        instance = get_object_or_404(self.get_queryset(), pk=self.kwargs['id'])
        if not self.allow_modifications(application.region):
            raise error_codes.UPDATE_CUSTOM_DOMAIN_FAILED.format('当前应用版本不允许手动管理独立域名，请联系平台管理员')

        data = validate_domain_payload(request.data, application, serializer_cls=DomainForUpdateSLZ, instance=instance)
        new_instance = get_custom_domain_mgr(application).update(
            instance, host=data['name'], path_prefix=data['path_prefix'], https_enabled=data['https_enabled']
        )
        return Response(DomainSLZ(new_instance).data)

    @swagger_auto_schema(operation_id="delete-app-domain", responses={204: openapi_empty_response}, tags=['Domains'])
    def destroy(self, request, *args, **kwargs):
        """通过 ID 删除一个独立域名"""
        application = self.get_application()
        instance = get_object_or_404(self.get_queryset(), pk=self.kwargs['id'])
        if not self.allow_modifications(application.region):
            raise error_codes.DELETE_CUSTOM_DOMAIN_FAILED.format('当前应用版本不允许手动管理独立域名，请联系平台管理员')

        get_custom_domain_mgr(application).delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def allow_modifications(region) -> bool:
        """Whether modifying custom_domain is allowed"""
        conf = get_custom_domain_config(region)
        return conf.allow_user_modifications
