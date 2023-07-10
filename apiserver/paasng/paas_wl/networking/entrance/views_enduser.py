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
from rest_framework.viewsets import GenericViewSet, ViewSet

from paas_wl.cluster.shim import EnvClusterService
from paas_wl.networking.entrance import serializers as slzs
from paas_wl.networking.entrance.addrs import URL, Address
from paas_wl.networking.entrance.allocator.domains import SubDomainAllocator
from paas_wl.networking.entrance.allocator.subpaths import SubPathAllocator
from paas_wl.networking.entrance.constants import AddressType
from paas_wl.networking.entrance.serializers import DomainForUpdateSLZ, DomainSLZ, validate_domain_payload
from paas_wl.networking.entrance.shim import LiveEnvAddresses, get_highest_priority_builtin_address
from paas_wl.networking.ingress.config import get_custom_domain_config
from paas_wl.networking.ingress.domains.manager import get_custom_domain_mgr
from paas_wl.networking.ingress.models import Domain
from paas_wl.workloads.processes.controllers import env_is_running
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.views import ApplicationCodeInPathMixin
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.region.models import get_region
from paasng.utils.api_docs import openapi_empty_response
from paasng.utils.error_codes import error_codes

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

    @swagger_auto_schema(response_serializer=slzs.ModuleEntrancesSLZ(many=True), tags=["访问入口"])
    def list_all_entrances(self, request, code):
        """查看应用所有模块的访问入口"""
        application = self.get_application()
        all_entrances = []
        for module in application.modules.all():
            module_entrances = {"name": module.name, "is_default": module.is_default, "envs": {}}
            all_entrances.append(module_entrances)
            for env in module.envs.all():
                env_entrances = module_entrances["envs"].setdefault(env.environment, [])
                is_running = env_is_running(env)
                addresses = []
                # 每个环境仅展示一个内置访问地址
                _, builtin_address = get_highest_priority_builtin_address(env)
                if builtin_address:
                    addresses.append(builtin_address)
                else:
                    # 除非集群的配置有问题, 理论上 builtin_address 不会为空
                    logger.error(
                        "builtin address is None for application %s module %s env %s",
                        application.code,
                        module.name,
                        env.environment,
                    )
                addresses.extend(LiveEnvAddresses(env).list_custom())
                for address in addresses:
                    env_entrances.append(
                        {
                            "module": module.name,
                            "env": env.environment,
                            "address": address,
                            "is_running": is_running,
                        }
                    )
        return Response(data=slzs.ModuleEntrancesSLZ(all_entrances, many=True).data)

    @swagger_auto_schema(response_serializer=slzs.AvailableEntranceSLZ(many=True), tags=["访问入口"])
    def list_module_available_entrances(self, request, code, module_name):
        """查看将 module_name 模块作为默认访问模块时可选的入口

        - 平台内置短地址
        - 独立域名
        """
        application = self.get_application()
        module = application.get_module(module_name)
        prod_env = module.get_envs("prod")
        ingress_config = EnvClusterService(prod_env).get_cluster().ingress_config
        region = get_region(application.region)
        default_entrance: Address
        if region.entrance_config.exposed_url_type == ExposedURLType.SUBDOMAIN:
            domain = SubDomainAllocator(code, ingress_config.port_map).for_default_module_prod_env(
                ingress_config.app_root_domains[-1]
            )
            default_entrance = Address(
                type=AddressType.SUBDOMAIN,
                url=domain.as_url().as_address(),
            )
        elif region.entrance_config.exposed_url_type == ExposedURLType.SUBPATH:
            subpath = SubPathAllocator(code, ingress_config.port_map).for_default_module_prod_env(
                ingress_config.app_root_domains[-1]
            )
            default_entrance = Address(
                type=AddressType.SUBPATH,
                url=subpath.as_url().as_address(),
            )
        else:
            raise NotImplementedError
        custom_domains_qs = Domain.objects.filter(environment_id=prod_env.id)
        custom_domains = []
        for d in custom_domains_qs:
            port = ingress_config.port_map.get_port_num(d.protocol)
            custom_domains.append(
                Address(
                    type=AddressType.CUSTOM,
                    url=URL(d.protocol, hostname=d.name, port=port, path=d.path_prefix).as_address(),
                    id=d.id,
                )
            )
        return Response(data=slzs.AvailableEntranceSLZ([default_entrance, *custom_domains], many=True).data)
