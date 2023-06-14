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

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from paas_wl.cluster.shim import EnvClusterService
from paas_wl.networking.entrance import serializers as slzs
from paas_wl.networking.entrance.addrs import EnvAddresses
from paas_wl.networking.entrance.constants import AddressType
from paas_wl.networking.entrance.serializers import DomainForUpdateSLZ, DomainSLZ, validate_domain_payload
from paas_wl.networking.ingress.config import get_custom_domain_config
from paas_wl.networking.ingress.domains.manager import get_custom_domain_mgr
from paas_wl.networking.ingress.models import Domain
from paas_wl.workloads.processes.controllers import env_is_running
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.signals import application_default_module_switch
from paasng.platform.applications.views import ApplicationCodeInPathMixin
from paasng.publish.market.constant import ProductSourceUrlType
from paasng.publish.market.models import MarketConfig
from paasng.publish.market.protections import ModulePublishPreparer
from paasng.utils.api_docs import openapi_empty_response
from paasng.utils.error_codes import error_codes
from paasng.utils.views import permission_classes as perm_classes

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

    @swagger_auto_schema(response_serializer=slzs.CustomDomainsConfigSLZ(many=True), tags=["访问入口"])
    def list_configs(self, request, code):
        """查看独立域名相关配置信息，比如前端负载均衡 IP 地址等"""
        application = self.get_application()
        results = []
        for module in application.modules.all():
            for env in module.envs.all():
                cluster = EnvClusterService(env).get_cluster()
                # `cluster` could be None when application's engine was disabled
                frontend_ingress_ip = cluster.ingress_config.frontend_ingress_ip if cluster else ''
                results.append(
                    {
                        'module': module.name,
                        'environment': env.environment,
                        'frontend_ingress_ip': frontend_ingress_ip,
                    }
                )
        return Response(slzs.CustomDomainsConfigSLZ(results, many=True).data)

    @staticmethod
    def allow_modifications(region) -> bool:
        """Whether modifying custom_domain is allowed"""
        conf = get_custom_domain_config(region)
        return conf.allow_user_modifications


class AppEntranceViewSet(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(response_serializer=slzs.ModuleEnvAddressSLZ(many=True), tags=["访问入口"])
    def list_all_entrances(self, request, code):
        """查看应用所有模块的访问入口"""
        application = self.get_application()
        results = []
        for module in application.modules.all():
            for env in module.envs.all():
                addresses = EnvAddresses(env).get()
                for address in addresses:
                    results.append(
                        {
                            "module": module.name,
                            "env": env.environment,
                            "address": address,
                            "is_running": env_is_running(env),
                        }
                    )
        return Response(data=slzs.ModuleEnvAddressSLZ(results, many=True).data)

    @swagger_auto_schema
    def list_module_all_entrances(self, request, code, module_name):
        """查看应用指定模块的访问入口

        - 平台内置短地址
        - 独立域名
        """
        raise NotImplementedError

    @atomic
    @perm_classes([application_perm_class(AppAction.MANAGE_MODULE)], policy='merge')
    @swagger_auto_schema(request_body=slzs.SwitchDefaultEntranceSLZ, tags=["访问入口"])
    def set_default_entrance(self, request, code):
        """设置某个模块为主模块"""
        slz = slzs.SwitchDefaultEntranceSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        application = self.get_application()
        default_module = application.get_default_module_with_lock()
        try:
            module = application.get_module_with_lock(module_name=data["module"])
        except ObjectDoesNotExist:
            # 可能在设置之前模块已经被删除了
            raise error_codes.CANNOT_SET_DEFAULT.f(_("{module_name} 模块已经被删除").format(module_name=data["module"]))

        # 验证独立域名
        address = data["address"]
        if address["type"] == AddressType.CUSTOM:
            url = address["url"]
            if not EnvAddresses(module.get_envs("prod")).validate_custom_url(address["url"]):
                raise error_codes.CANNOT_SET_DEFAULT.f(
                    _("{url} 并非 {module_name} 模块的访问入口").format(url=url, module_name=module.name)
                )

        market_config, __ = MarketConfig.objects.get_or_create_by_app(application)
        # 切换默认访问模块
        if module.name != default_module.name:
            if market_config.enabled and not ModulePublishPreparer(module).all_matched:
                raise error_codes.CANNOT_SET_DEFAULT.f(
                    _("目标 {module_name} 模块未满足应用市场服务开启条件，切换默认访问模块会导致应用在市场中访问异常").format(module_name=module.name)
                )
            logger.info(
                f'Switching default module for application[{application.code}], '
                f'{default_module.name} -> {module.name}...'
            )
            default_module.is_default = False
            module.is_default = True
            module.save(update_fields=["is_default", "updated"])
            default_module.save(update_fields=["is_default", "updated"])
            application_default_module_switch.send(
                sender=application, application=application, new_module=module, old_module=default_module
            )

        # 保存市场信息
        if address["type"] == AddressType.CUSTOM:
            market_config.custom_domain_url = address["url"]
            market_config.source_url_type = ProductSourceUrlType.CUSTOM_DOMAIN
        else:
            market_config.source_url_type = ProductSourceUrlType.ENGINE_PROD_ENV
        market_config.save()
        return Response()
