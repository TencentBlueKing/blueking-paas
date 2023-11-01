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
from typing import Dict, List, Optional, Union, cast

from django.http.response import Http404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from paas_wl.infras.cluster.utils import get_cluster_by_app
from paasng.accessories.publish.entrance.exposer import get_exposed_links
from paasng.accessories.servicehub.manager import ServiceObjNotFound, SvcAttachmentDoesNotExist, mixed_service_mgr
from paasng.accessories.servicehub.services import ServiceObj, ServiceSpecificationHelper
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_required
from paasng.infras.accounts.utils import ForceAllowAuthedApp
from paasng.plat_admin.system.applications import (
    SimpleAppSource,
    query_uni_apps_by_ids,
    query_uni_apps_by_keyword,
    query_uni_apps_by_username,
)
from paasng.plat_admin.system.serializers import (
    AddonCredentialsSLZ,
    AddonSpecsSLZ,
    ClusterNamespaceSLZ,
    ContactInfo,
    MinimalAppSLZ,
    QueryUniApplicationsByID,
    QueryUniApplicationsByUserName,
    SearchApplicationSLZ,
    UniversalAppSLZ,
)
from paasng.plat_admin.system.utils import MaxLimitOffsetPagination
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application
from paasng.platform.applications.operators import get_contact_info
from paasng.platform.engine.phases_steps.display_blocks import ServicesInfo
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


@ForceAllowAuthedApp.mark_view_set
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

        results = query_uni_apps_by_ids(ids=data['id'], include_inactive_apps=data['include_inactive_apps'])
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
                    deploy_info = get_exposed_links(app._db_object)

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

    @swagger_auto_schema(
        tags=['SYSTEMAPI'], responses={200: MinimalAppSLZ(many=True)}, query_serializer=SearchApplicationSLZ
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

        keyword = data.get('keyword')
        include_inactive_apps = data.get('include_inactive_apps')
        applications = query_uni_apps_by_keyword(keyword, offset, limit, include_inactive_apps)

        # Paginate results
        applications = paginator.paginate_queryset(applications, request, self)
        serializer = MinimalAppSLZ(applications, many=True)
        return paginator.get_paginated_response(serializer.data)


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
        return Response(data=AddonCredentialsSLZ({"credentials": credentials}).data)

    @swagger_auto_schema(tags=["SYSTEMAPI"], request_body=AddonSpecsSLZ)
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

        try:
            mixed_service_mgr.get_module_rel(service_id=svc.uuid, module_id=module.id)
        except SvcAttachmentDoesNotExist:
            # 如果未启用增强服务, 则静默启用
            serializer = AddonSpecsSLZ(data=request.data, context={'svc': svc})
            serializer.is_valid(raise_exception=True)
            specs = serializer.validated_data['specs'] or self._get_pub_recommended_specs(svc)
            try:
                mixed_service_mgr.bind_service(svc, module, specs)
            except Exception as e:
                logger.exception("bind service %s to module %s error %s", svc.uuid, module.name, e)
                raise error_codes.CANNOT_BIND_SERVICE.f(str(e))

        # 如果未分配增强服务实例, 则进行分配
        rel = next(mixed_service_mgr.list_unprovisioned_rels(engine_app, service=svc), None)
        if not rel:
            return Response(data={'service_id': svc.uuid}, status=status.HTTP_200_OK)

        rel.provision()
        return Response(data={'service_id': svc.uuid}, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["SYSTEMAPI"])
    @site_perm_required(SiteAction.SYSAPI_READ_SERVICES)
    def list_services(self, request, code, module_name, environment):
        """查询增强服务启用/实例分配情况"""
        engine_app = self.get_engine_app_via_path()
        service_info = ServicesInfo.get_detail(engine_app)['services_info']
        return Response(data=service_info)

    @swagger_auto_schema(tags=["SYSTEMAPI"])
    @site_perm_required(SiteAction.SYSAPI_READ_SERVICES)
    def retrieve_specs(self, request, code, module_name, service_id):
        """获取应用已绑定的服务规格.
        接口实现逻辑参考 paasng.accessories.servicehub.views.ModuleServicesViewSet.retrieve_specs
        """
        application = self.get_application()
        module = self.get_module_via_path()
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
        return Response({'results': spec_data})

    @staticmethod
    def _get_pub_recommended_specs(svc: ServiceObj) -> Optional[dict]:
        """获取增强服务的推荐 specs"""
        if not svc.public_specifications:
            return None
        # get_recommended_spec 可能会生成 value 是 None 的 spec
        return ServiceSpecificationHelper.from_service_public_specifications(svc).get_recommended_spec()


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


class ClusterNamespaceInfoView(ApplicationCodeInPathMixin, viewsets.ViewSet):
    """System api for query app cluster/namespace info"""

    @swagger_auto_schema(tags=["SYSTEMAPI"], responses={"200": ClusterNamespaceSLZ(many=True)})
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list_by_app_code(self, request, code):
        """list app cluster/namespace info"""
        application = self.get_application()
        wl_apps = [env.wl_app for env in application.envs.all()]

        namespace_cluster_map: Dict[str, str] = {}
        for wl_app in wl_apps:
            if (ns := wl_app.namespace) not in namespace_cluster_map:
                namespace_cluster_map[ns] = get_cluster_by_app(wl_app).bcs_cluster_id or ''

        data = [
            {'namespace': ns, 'bcs_cluster_id': bcs_cluster_id} for ns, bcs_cluster_id in namespace_cluster_map.items()
        ]
        return Response(ClusterNamespaceSLZ(data, many=True).data)
