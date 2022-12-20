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
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.helpers import get_module_prod_env_root_domains
from paasng.publish.entrance.exposer import (
    get_deployed_status,
    get_preallocated_urls,
    update_exposed_url_type_to_subdomain,
)
from paasng.publish.entrance.serializers import (
    ApplicationAvailableEntranceSLZ,
    ApplicationCustomDomainEntranceSLZ,
    ApplicationDefaultEntranceSLZ,
    PreferredRootDoaminSLZ,
    RootDoaminSLZ,
    UpdateExposedURLTypeSLZ,
)
from paasng.publish.market.utils import ModuleEnvAvailableAddressHelper


class ExposedURLTypeViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """管理模块访问地址类型"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def update(self, request, code, module_name):
        """更新模块由平台提供的访问地址的类型"""
        application = self.get_application()
        module = application.get_module(module_name)

        serializer = UpdateExposedURLTypeSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.data['exposed_url_type'] == ExposedURLType.SUBDOMAIN:
            if module.exposed_url_type == ExposedURLType.SUBDOMAIN:
                raise ValidationError(_('当前模块访问地址已经是子域名类型，无需修改'))

            update_exposed_url_type_to_subdomain(module)
        return Response({})


class ApplicationAvailableAddressViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """一个提供应用所有访问入口的ViewSet, 访问入口包括:
    -   由平台默认提供的地址(与模块环境 1v1 对应）
    -   由用户设置的独立域名地址(与模块环境存在 1vN 关系)
    """

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(responses={'200': ApplicationAvailableEntranceSLZ()}, tags=["访问入口"])
    def list_module_default_entrances(self, request, code, module_name):
        """查看模块的默认的所有访问入口(由平台提供的)，无论是否运行"""
        module = self.get_module_via_path()
        deployed_status = get_deployed_status(module)

        def get_plain_entrance():
            # 默认 stag 在 prod 之前创建
            for env in module.envs.all().order_by("id"):
                yield from [
                    dict(
                        env=env.environment,
                        is_running=deployed_status.get(env.environment, False),
                        address=entrance.address,
                    )
                    for entrance in get_preallocated_urls(env)
                ]

        return Response(
            data=dict(
                ApplicationAvailableEntranceSLZ(
                    {
                        # 2019-08-05 之前创建的模块该字段为 null，只要切换过就一定会有值
                        "type": module.exposed_url_type or ExposedURLType.SUBPATH,
                        "entrances": list(get_plain_entrance()),
                    }
                ).data
            )
        )

    @swagger_auto_schema(responses={'200': ApplicationDefaultEntranceSLZ(many=True)}, tags=["访问入口"])
    def list_default_entrance(self, request, code):
        """查看应用所有模块的默认的访问入口(由平台提供的)"""
        application = self.get_application()
        results = []
        for module in application.modules.all():
            results.extend(
                [
                    dict(
                        env=env.environment,
                        module=module,
                        address=ModuleEnvAvailableAddressHelper(env).default_access_entrance,
                    )
                    for env in module.envs.all()
                    if env.is_running()
                ]
            )
        return Response(ApplicationDefaultEntranceSLZ(results, many=True).data)

    @swagger_auto_schema(responses={'200': ApplicationCustomDomainEntranceSLZ(many=True)}, tags=["访问入口"])
    def list_custom_domain_entrance(self, request, code):
        """查看应用所有的独立域名访问入口"""
        application = self.get_application()
        results = []
        for module in application.modules.all():
            results.extend(
                [
                    dict(
                        env=env.environment,
                        module=module,
                        addresses=ModuleEnvAvailableAddressHelper(env).domain_addresses,
                    )
                    for env in module.envs.all()
                    if env.is_running()
                ]
            )
        return Response(ApplicationCustomDomainEntranceSLZ(results, many=True).data)


class ModuleRootDomainsViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(responses={'200': RootDoaminSLZ()}, tags=["访问入口"])
    def get(self, request, code, module_name):
        """
        查看模块所属集群的子域名根域名和当前模块的偏好的根域名
        NOTE: 已确认偏好根域名设置仅影响生产环境访问，因此只取生产环境可用的根域名
        """
        module = self.get_module_via_path()
        if module.exposed_url_type is None:
            return Response(status=HTTP_204_NO_CONTENT)

        switchable_domains = [
            domain.name for domain in get_module_prod_env_root_domains(module, include_reserved=False)
        ]
        preferred_root_domain = module.user_preferred_root_domain

        # 模块没有设置偏好根域名，则默认为集群设置的第一个根域
        if not preferred_root_domain and switchable_domains:
            preferred_root_domain = switchable_domains[0]

        # 如果当前的域名是保留域名, 那么则添加到
        if preferred_root_domain not in switchable_domains:
            switchable_domains.append(preferred_root_domain)

        return Response(
            data=RootDoaminSLZ(
                {
                    "root_domains": switchable_domains,
                    "preferred_root_domain": preferred_root_domain,
                }
            ).data
        )


class ModulePreferredRootDomainsViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def update(self, request, code, module_name):
        """
        更新模块的偏好根域
        NOTE: 已确认偏好根域名设置仅影响生产环境访问，因此只取生产环境可用的根域名
        """
        module = self.get_module_via_path()
        root_domains = get_module_prod_env_root_domains(module, include_reserved=True)

        serializer = PreferredRootDoaminSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        preferred_root_domain: str = serializer.data['preferred_root_domain']

        for domain in root_domains:
            if domain.name == preferred_root_domain and not domain.reserved:
                break
        else:
            raise ValidationError(_('不支持切换至该域名'))

        module.user_preferred_root_domain = preferred_root_domain
        module.save()

        return Response(status=HTTP_204_NO_CONTENT)
