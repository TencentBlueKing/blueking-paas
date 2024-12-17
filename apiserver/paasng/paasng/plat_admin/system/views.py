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
from typing import Any, Dict, List, Optional, cast

from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from paas_wl.infras.cluster.utils import get_cluster_by_app
from paasng.accessories.publish.entrance.exposer import get_exposed_links
from paasng.accessories.publish.market.models import MarketConfig
from paasng.accessories.publish.market.utils import MarketAvailableAddressHelper
from paasng.accessories.servicehub.manager import ServiceObjNotFound, SvcAttachmentDoesNotExist, mixed_service_mgr
from paasng.accessories.servicehub.services import ServiceObj, ServiceSpecificationHelper
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_required
from paasng.infras.accounts.utils import ForceAllowAuthedApp
from paasng.plat_admin.system.applications import (
    SimpleAppSource,
    UniSimpleApp,
    query_uni_apps_by_ids,
    query_uni_apps_by_keyword,
    query_uni_apps_by_username,
)
from paasng.plat_admin.system.serializers import (
    AddonCredentialsSLZ,
    AddonSpecsSLZ,
    ClusterNamespaceSLZ,
    ContactInfoSLZ,
    MinimalAppSLZ,
    QueryUniApplicationsByID,
    QueryUniApplicationsByUserName,
    SearchApplicationSLZ,
    UniversalAppSLZ,
)
from paasng.plat_admin.system.utils import MaxLimitOffsetPagination
from paasng.platform.applications.models import Application
from paasng.platform.applications.operators import get_contact_info_by_appids
from paasng.platform.engine.phases_steps.display_blocks import ServicesInfo
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


@ForceAllowAuthedApp.mark_view_set
class SysUniApplicationViewSet(viewsets.ViewSet):
    """System universal application view sets"""

    def get_contact_info_data(self, application: Application, app_source: SimpleAppSource, contact_info_dict: dict):
        # PaaS2.0 应用的联系人信息固定为 None
        if app_source == SimpleAppSource.DEFAULT:
            contact_info = contact_info_dict.get(application.code)
            return ContactInfoSLZ(contact_info).data if contact_info else None
        return None

    def get_deploy_info_data(self, application: Application, app_source: SimpleAppSource):
        # PaaS2.0 应用的部署信息固定为 None
        if app_source == SimpleAppSource.DEFAULT:
            deploy_info = get_exposed_links(application)
            return deploy_info if deploy_info else None
        return None

    def get_market_address(self, application: Application, app_source: SimpleAppSource) -> Optional[str]:
        """应用市场地址"""
        # PaaS2.0 应用直接返回 None
        if app_source == SimpleAppSource.LEGACY:
            return None

        market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
        access_entrance = MarketAvailableAddressHelper(market_config).access_entrance
        if access_entrance:
            return access_entrance.address
        else:
            return None

    def serialize_app_details(
        self,
        app: UniSimpleApp,
        contact_info_dict: Optional[dict],
        include_deploy_info: bool,
        include_market_info: bool,
    ):
        app_data = UniversalAppSLZ(app).data
        app_instance = cast(Application, app._db_object)

        # 返回数据中是否包含联系人信息, contact_info_dict 为 None 代表不返回联系人信息
        if contact_info_dict is not None:
            app_data["contact_info"] = self.get_contact_info_data(app_instance, app._source, contact_info_dict)

        # 返回数据总是否包含部署信息
        if include_deploy_info:
            app_data["deploy_info"] = self.get_deploy_info_data(app_instance, app._source)
        # 添加应用市场地址信息
        if include_market_info:
            app_data["market_addres"] = self.get_market_address(app_instance, app._source)
        return app_data

    @swagger_auto_schema(
        tags=["SYSTEMAPI"], responses={200: UniversalAppSLZ(many=True)}, query_serializer=QueryUniApplicationsByID
    )
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def query_by_id(self, request):
        request_serializer = QueryUniApplicationsByID(data=request.query_params)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # 获取请求参数
        app_ids = request_data["id"]
        include_inactive_apps = request_data["include_inactive_apps"]
        include_deploy_info = request_data["include_deploy_info"]
        include_developers_info = request_data["include_developers_info"]
        include_contact_info = request_data["include_contact_info"]
        include_market_info = request_data["include_market_info"]

        # 查询应用信息
        uni_apps = query_uni_apps_by_ids(app_ids, include_inactive_apps, include_developers_info)
        # 所有应用联系人信息（不包含 PaaS2.0 应用）
        contact_info_dict = get_contact_info_by_appids(app_ids) if include_contact_info else None
        app_details: List[Optional[Dict[str, Any]]] = [
            self.serialize_app_details(app, contact_info_dict, include_deploy_info, include_market_info)
            if app is not None
            else None
            for app_id in app_ids
            for app in [uni_apps.get(app_id)]
        ]

        return Response(app_details, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["SYSTEMAPI"],
        responses={200: UniversalAppSLZ(many=True)},
        query_serializer=QueryUniApplicationsByUserName,
    )
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def query_by_username(self, request):
        """根据 username 查询多平台应用信息"""
        serializer = QueryUniApplicationsByUserName(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        username = data["username"]
        uni_apps = query_uni_apps_by_username(username)
        return Response(UniversalAppSLZ(uni_apps, many=True).data)

    @swagger_auto_schema(
        tags=["SYSTEMAPI"], responses={200: MinimalAppSLZ(many=True)}, query_serializer=SearchApplicationSLZ
    )
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list_minimal_app(self, request):
        """查询多平台应用基本信息，可根据 id 或者 name 模糊搜索, 最多只返回 1000 条数据"""
        serializer = SearchApplicationSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        paginator = MaxLimitOffsetPagination()
        offset = paginator.get_offset(request)
        limit = paginator.get_limit(request)

        keyword = data.get("keyword")
        include_inactive_apps = data.get("include_inactive_apps")
        applications = query_uni_apps_by_keyword(keyword, offset, limit, include_inactive_apps)

        # Paginate results
        applications = paginator.paginate_queryset(applications, request, self)
        serializer = MinimalAppSLZ(applications, many=True)
        return paginator.get_paginated_response(serializer.data)


class SysAddonsAPIViewSet(viewsets.ViewSet):
    """System api for managing Application Addons"""

    @swagger_auto_schema(tags=["SYSTEMAPI"])
    @site_perm_required(SiteAction.SYSAPI_READ_SERVICES)
    def query_credentials(self, request, code, module_name, environment, service_name):
        """查询增强服务的 credentials 信息"""
        application = get_object_or_404(Application, code=code)
        engine_app = application.get_engine_app(environment, module_name=module_name)
        try:
            svc = mixed_service_mgr.find_by_name(name=service_name, region=application.region)
        except ServiceObjNotFound:
            logger.info("service named '%s' not found", service_name)
            raise Http404(f"service named '{service_name}' not found")

        credentials = mixed_service_mgr.get_env_vars(engine_app=engine_app, service=svc)
        if not credentials:
            raise error_codes.CANNOT_READ_INSTANCE_INFO.f(_("无法获取到有效的配置信息."))
        return Response(data=AddonCredentialsSLZ({"credentials": credentials}).data)

    # 下一个大版本移除该接口
    @swagger_auto_schema(tags=["SYSTEMAPI"], request_body=AddonSpecsSLZ, deprecated=True)
    @site_perm_required(SiteAction.SYSAPI_READ_SERVICES)
    def provision_service(self, request, code, module_name, environment, service_name):
        """分配增强服务实例"""
        application = get_object_or_404(Application, code=code)
        module = application.get_module(module_name)
        engine_app = application.get_engine_app(environment, module_name=module_name)

        try:
            svc = mixed_service_mgr.find_by_name(name=service_name, region=application.region)
        except ServiceObjNotFound:
            raise error_codes.CANNOT_PROVISION_INSTANCE.f(f"addon named '{service_name}' not found")

        try:
            mixed_service_mgr.get_module_rel(service_id=svc.uuid, module_id=module.id)
        except SvcAttachmentDoesNotExist:
            # 如果未启用增强服务, 则静默启用
            serializer = AddonSpecsSLZ(data=request.data, context={"svc": svc})
            serializer.is_valid(raise_exception=True)
            specs = serializer.validated_data["specs"] or self._get_pub_recommended_specs(svc)
            try:
                mixed_service_mgr.bind_service(svc, module, specs)
            except Exception as e:
                logger.exception("bind service %s to module %s error.", svc.uuid, module.name)
                raise error_codes.CANNOT_BIND_SERVICE.f(str(e))

        # 如果未分配增强服务实例, 则进行分配
        rel = next(mixed_service_mgr.list_unprovisioned_rels(engine_app, service=svc), None)
        if not rel:
            return Response(data={"service_id": svc.uuid}, status=status.HTTP_200_OK)

        rel.provision()
        return Response(data={"service_id": svc.uuid}, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["SYSTEMAPI"])
    @site_perm_required(SiteAction.SYSAPI_READ_SERVICES)
    def list_services(self, request, code, module_name, environment):
        """查询增强服务启用/实例分配情况"""
        application = get_object_or_404(Application, code=code)
        engine_app = application.get_engine_app(environment, module_name=module_name)

        service_info = ServicesInfo.get_detail(engine_app)["services_info"]
        return Response(data=service_info)

    # 下一个大版本移除该接口
    @swagger_auto_schema(tags=["SYSTEMAPI"], deprecated=True)
    @site_perm_required(SiteAction.SYSAPI_READ_SERVICES)
    def retrieve_specs_by_uuid(self, request, code, module_name, service_id):
        """获取应用已绑定的服务规格.
        接口实现逻辑参考 paasng.accessories.servicehub.views.ModuleServicesViewSet.retrieve_specs
        """
        application = get_object_or_404(Application, code=code)
        module = application.get_module(module_name)
        service = mixed_service_mgr.get_or_404(service_id, region=application.region)

        # 如果模块与增强服务之间没有绑定关系，直接返回 404 状态码
        if not mixed_service_mgr.module_is_bound_with(service, module):
            raise Http404

        specs = {}
        for env in module.envs.all():
            for rel in mixed_service_mgr.list_all_rels(env.engine_app, service_id=service_id):
                plan = rel.get_plan()
                specs = plan.specifications
                break  # 现阶段所有环境的服务规格一致，因此只需要拿一个

        spec_data: Dict[str, Optional[str]] = {
            definition.name: specs.get(definition.name) for definition in service.specifications
        }
        return Response({"results": spec_data})

    @staticmethod
    def _get_pub_recommended_specs(svc: ServiceObj) -> Optional[dict]:
        """获取增强服务的推荐 specs"""
        if not svc.public_specifications:
            return None
        # get_recommended_spec 可能会生成 value 是 None 的 spec
        return ServiceSpecificationHelper.from_service_public_specifications(svc).get_recommended_spec()


class LessCodeSystemAPIViewSet(viewsets.ViewSet):
    """System api for lesscode"""

    @swagger_auto_schema(tags=["SYSTEMAPI", "LESSCODE"])
    @site_perm_required(SiteAction.SYSAPI_READ_DB_CREDENTIAL)
    def query_db_credentials(self, request, code, module_name, environment):
        """查询数据库增强服务的 credentials 信息"""
        application = get_object_or_404(Application, code=code)
        svc = self.get_db_service(application)

        engine_app = application.get_engine_app(environment, module_name=module_name)

        credentials = mixed_service_mgr.get_env_vars(engine_app=engine_app, service=svc)
        if not credentials:
            raise error_codes.CANNOT_READ_INSTANCE_INFO.f(_("无法获取到有效的配置信息."))
        return Response(data={"credentials": credentials})

    @swagger_auto_schema(tags=["SYSTEMAPI", "LESSCODE"])
    @site_perm_required(SiteAction.SYSAPI_BIND_DB_SERVICE)
    def bind_db_service(self, request, code, module_name):
        """尝试绑定数据库增强服务"""
        application = get_object_or_404(Application, code=code)
        module = application.get_module(module_name)

        svc = self.get_db_service(application)

        try:
            mixed_service_mgr.get_module_rel(service_id=svc.uuid, module_id=module.id)
        except SvcAttachmentDoesNotExist:
            mixed_service_mgr.bind_service(service=svc, module=module)
        return Response()

    def get_db_service(self, application):
        """获取数据库增强服务"""
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


class ClusterNamespaceInfoView(viewsets.ViewSet):
    """System api for query app cluster/namespace info"""

    @swagger_auto_schema(tags=["SYSTEMAPI"], responses={"200": ClusterNamespaceSLZ(many=True)})
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list_by_app_code(self, request, code):
        """list app cluster/namespace info"""
        application = get_object_or_404(Application, code=code)
        wl_apps = [env.wl_app for env in application.envs.all()]

        namespace_cluster_map: Dict[str, str] = {}
        for wl_app in wl_apps:
            if (ns := wl_app.namespace) not in namespace_cluster_map:
                namespace_cluster_map[ns] = get_cluster_by_app(wl_app).bcs_cluster_id or ""

        data = [
            {"namespace": ns, "bcs_cluster_id": bcs_cluster_id} for ns, bcs_cluster_id in namespace_cluster_map.items()
        ]
        return Response(ClusterNamespaceSLZ(data, many=True).data)
