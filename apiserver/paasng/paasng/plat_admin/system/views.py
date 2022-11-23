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
from dataclasses import asdict
from typing import Dict, List, Union, cast

from django.conf import settings
from django.http.response import Http404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_required
from paasng.dev_resources.servicehub.manager import ServiceObjNotFound, SvcAttachmentDoesNotExist, mixed_service_mgr
from paasng.engine.deploy.infras import AppDefaultDomains, AppDefaultSubpaths
from paasng.engine.display_blocks import ServicesInfo
from paasng.engine.models.config_var import generate_builtin_env_vars
from paasng.plat_admin.system.applications import (
    SimpleAppSource,
    get_contact_info,
    query_uni_apps_by_ids,
    query_uni_apps_by_username,
)
from paasng.plat_admin.system.serializers import (
    AppBasicSLZ,
    ContactInfo,
    ModuleBasicSLZ,
    ModuleEnvBasicSLZ,
    QueryApplicationsSLZ,
    QueryUniApplicationsByID,
    QueryUniApplicationsByUserName,
    UniversalAppSLZ,
)
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.models import Module
from paasng.publish.market.models import MarketConfig
from paasng.publish.market.utils import MarketAvailableAddressHelper
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class SysUniApplicationViewSet(viewsets.ViewSet):
    """System universal application view sets"""

    @swagger_auto_schema(
        tags=['SYSTEMAPI'], responses={200: UniversalAppSLZ(many=True)}, query_serializer=QueryUniApplicationsByID
    )
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def query_by_id(self, request):
        """根据应用 ID（Code）查询多平台应用信息"""
        serializer = QueryUniApplicationsByID(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        include_deploy_info = data['include_deploy_info']

        results = query_uni_apps_by_ids(data['id'])
        json_apps: List[Union[None, Dict]] = []
        for app_id in data['id']:
            app = results.get(app_id)
            if not app:
                json_apps.append(None)
                continue

            contact_info = None
            deploy_info = None
            basic_info = UniversalAppSLZ(app).data
            if app._source == SimpleAppSource.DEFAULT:
                app._db_object = cast(Application, app._db_object)

                contact_info = get_contact_info(app._db_object)
                contact_info = ContactInfo(contact_info).data

                # 部署信息中的访问地址信息很耗时，所以指定参数时才返回
                if include_deploy_info:
                    deploy_info = app._db_object.get_deploy_info()

            basic_info['contact_info'] = contact_info
            if include_deploy_info:
                basic_info['deploy_info'] = deploy_info

            json_apps.append(basic_info)
        return Response(json_apps)

    @swagger_auto_schema(
        tags=['SYSTEMAPI'],
        responses={200: UniversalAppSLZ(many=True)},
        query_serializer=QueryUniApplicationsByUserName,
    )
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def query_by_username(self, request):
        """根据 username 查询多平台应用信息"""
        serializer = QueryUniApplicationsByUserName(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        username = data['username']
        uni_apps = query_uni_apps_by_username(username)
        return Response(UniversalAppSLZ(uni_apps, many=True).data)


class SysAddonsAPIViewSet(ApplicationCodeInPathMixin, viewsets.ViewSet):
    """System api for managing Application Addons"""

    @swagger_auto_schema(tags=["SYSTEMAPI"])
    @site_perm_required(SiteAction.SYSAPI_READ_SERVICES)
    def query_credentials(self, request, code, module_name, environment, service_name):
        """查询增强服务的 credentials 信息"""
        application = self.get_application()
        engine_app = self.get_engine_app_via_path()
        try:
            svc = mixed_service_mgr.find_by_name(name=service_name, region=application.region)
        except ServiceObjNotFound:
            logger.info("service named '%s' not found", service_name)
            raise Http404(f"service named '{service_name}' not found")

        credentials = mixed_service_mgr.get_env_vars(engine_app=engine_app, service=svc)
        if not credentials:
            raise error_codes.CANNOT_READ_INSTANCE_INFO.f(_("无法获取到有效的配置信息."))
        return Response(data={"credentials": credentials})

    @swagger_auto_schema(tags=["SYSTEMAPI"])
    @site_perm_required(SiteAction.SYSAPI_READ_SERVICES)
    def provision_service(self, request, code, module_name, environment, service_name):
        """分配增强服务实例"""
        application = self.get_application()
        module = self.get_module_via_path()
        engine_app = self.get_engine_app_via_path()

        try:
            svc = mixed_service_mgr.find_by_name(name=service_name, region=application.region)
        except ServiceObjNotFound:
            raise error_codes.CANNOT_PROVISION_INSTANCE.f(f"addon named '{service_name}' not found")

        # 如果未启用增强服务, 则静默启用
        try:
            mixed_service_mgr.get_module_rel(service_id=svc.uuid, module_id=module.id)
        except SvcAttachmentDoesNotExist:
            raise error_codes.CANNOT_PROVISION_INSTANCE.f("addon is unbound")

        # 如果未分配增强服务实例, 则进行分配
        rel = next(mixed_service_mgr.list_unprovisioned_rels(engine_app, service=svc), None)
        if not rel:
            return Response(status=status.HTTP_204_NO_CONTENT)

        rel.provision()
        return Response(status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["SYSTEMAPI"])
    @site_perm_required(SiteAction.SYSAPI_READ_SERVICES)
    def list_services(self, request, code, module_name, environment):
        """查询增强服务启用/实例分配情况"""
        engine_app = self.get_engine_app_via_path()
        service_info = ServicesInfo.get_detail(engine_app)['services_info']
        return Response(data=service_info)


class LessCodeSystemAPIViewSet(ApplicationCodeInPathMixin, viewsets.ViewSet):
    """System api for lesscode"""

    @swagger_auto_schema(tags=["SYSTEMAPI", "LESSCODE"])
    @site_perm_required(SiteAction.SYSAPI_READ_DB_CREDENTIAL)
    def query_db_credentials(self, request, code, module_name, environment):
        """查询数据库增强服务的 credentials 信息"""
        svc = self.get_db_service()
        engine_app = self.get_engine_app_via_path()

        credentials = mixed_service_mgr.get_env_vars(engine_app=engine_app, service=svc)
        if not credentials:
            raise error_codes.CANNOT_READ_INSTANCE_INFO.f(_("无法获取到有效的配置信息."))
        return Response(data={"credentials": credentials})

    @swagger_auto_schema(tags=["SYSTEMAPI", "LESSCODE"])
    @site_perm_required(SiteAction.SYSAPI_BIND_DB_SERVICE)
    def bind_db_service(self, request, code, module_name):
        """尝试绑定数据库增强服务"""
        svc = self.get_db_service()
        module = self.get_module_via_path()

        try:
            mixed_service_mgr.get_module_rel(service_id=svc.uuid, module_id=module.id)
        except SvcAttachmentDoesNotExist:
            mixed_service_mgr.bind_service(service=svc, module=module)
        return Response()

    def get_db_service(self):
        """获取数据库增强服务"""
        application = self.get_application()
        svc = None
        for service_name in ["gcs_mysql", "mysql"]:
            try:
                svc = mixed_service_mgr.find_by_name(name=service_name, region=application.region)
            except ServiceObjNotFound:
                continue
            break

        if svc is None:
            raise Http404("DB Service Not Found!")
        return svc


class SysApplicationViewSet(viewsets.ViewSet):
    """System application view sets"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def query(self, request):
        """查询应用的模块、环境等信息"""
        serializer = QueryApplicationsSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data['code']:
            indexes = data['code']
            apps_map = {app.code: app for app in Application.default_objects.filter(code__in=data['code'])}
        elif data['uuid']:
            indexes = data['uuid']
            apps_map = {app.id: app for app in Application.default_objects.filter(id__in=data['uuid'])}
        # Below conditions only allows a single query term
        elif module_id := data.get('module_id'):
            indexes = [module_id]
            try:
                apps_map = {module_id: Module.objects.get(pk=module_id).application}
            except Module.DoesNotExist:
                apps_map = {}
        elif env_id := data.get('env_id'):
            indexes = [env_id]
            try:
                apps_map = {env_id: ModuleEnvironment.objects.get(pk=env_id).application}
            except ModuleEnvironment.DoesNotExist:
                apps_map = {}
        elif engine_app_id := data.get('engine_app_id'):
            indexes = [engine_app_id]
            try:
                apps_map = {engine_app_id: ModuleEnvironment.objects.get(engine_app_id=engine_app_id).application}
            except ModuleEnvironment.DoesNotExist:
                apps_map = {}
        else:
            raise ValidationError('params invalid')

        results: List[Union[None, Dict]] = []
        for idx in indexes:
            app = apps_map.get(idx)
            if not app:
                results.append(None)
                continue

            item = {'application': AppBasicSLZ(app).data}

            modules = Module.objects.filter(application=app)
            item['modules'] = ModuleBasicSLZ(modules, many=True).data

            envs = ModuleEnvironment.objects.filter(module__in=modules)
            item['envs'] = ModuleEnvBasicSLZ(envs, many=True).data
            results.append(item)
        return Response(results)


class SysMarketViewSet(ApplicationCodeInPathMixin, viewsets.ViewSet):
    """System Market view sets"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def get_entrance(self, request, code):
        """获取某应用的蓝鲸市场访问入口地址"""
        application = self.get_application()
        market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
        entrance = MarketAvailableAddressHelper(market_config).access_entrance
        if not entrance:
            return Response({'entrance': None})
        else:
            return Response({'entrance': asdict(entrance)})


class ApplicationAddressViewSet(ApplicationCodeInPathMixin, viewsets.ViewSet):
    """本视图提供应用访问地址相关的接口
    TODO: Remove this ViewSet, move the algorithm to workloads
    """

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list_preallocated_addresses(self, request, code, module_name, environment):
        """获取给应用预分配的子域名和子路径
        Preallocated addresses contains sub-domains and sub-paths generated via platform's
        algorithm. The algorithm depends on application's cluster configs, such as
        "sub_path_domains" and "app_root_domains" properties in "ingress_config" field.
        """
        env = self.get_env_via_path()
        subdomains = [d.as_dict() for d in AppDefaultDomains(env).domains]
        subpaths = [d.as_dict() for d in AppDefaultSubpaths(env).subpaths]
        return Response({"subdomains": subdomains, "subpaths": subpaths})


class ApplicationBuiltinEnvViewSet(ApplicationCodeInPathMixin, viewsets.ViewSet):
    """本视图提供应用内置环境变量相关的接口"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list_builtin_envs(self, request, code, module_name, environment):
        engine_app = self.get_engine_app_via_path()
        return Response({"data": generate_builtin_env_vars(engine_app, settings.CONFIGVAR_SYSTEM_PREFIX)})
