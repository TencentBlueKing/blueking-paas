# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""应用态 (系统 API) 增强服务视图

这些接口注册在 `sys/api/` 路径下, 仅供 AIDEV / 运维等固定的系统调用, 鉴权依赖 sysapi_client.
"""

from django.http import Http404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from paasng.accessories.servicehub import serializers as slzs
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.remote.manager import (
    RemoteServiceInstanceMgr,
    RemoteServiceMgr,
    get_app_by_instance_name,
)
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.platform.applications.mixins import SysManagedAppInPathMixin
from paasng.platform.applications.serializers import ApplicationMembersInfoSLZ

from .api import get_module_service_instances


class SysModuleServicesViewSet(viewsets.ViewSet, SysManagedAppInPathMixin):
    """应用态增强服务接口"""

    permission_classes = [sysapi_client_perm_class(ClientAction.READ_AI_AGENT_APP)]

    @swagger_auto_schema(tags=["增强服务"], operation_id="sys_get_service_instance_by_module")
    def retrieve(self, request, code, module_name, service_id):
        """应用态查看应用模块与增强服务的绑定关系详情, 仅 AIDEV 可调用, 仅允许操作 AI Agent 应用"""
        module = self.get_managed_module_via_path()
        service = mixed_service_mgr.get_or_404(service_id)

        # 如果模块与增强服务之间没有绑定关系，直接返回 404 状态码
        if not mixed_service_mgr.module_is_bound_with(service, module):
            raise Http404

        # 应用态仅返回实例 config 等必要信息
        return Response(get_module_service_instances(module, service, slzs.SysServiceInstanceInfoSLZ))


class SysRelatedApplicationsInfoViewSet(viewsets.ViewSet):
    permission_classes = [sysapi_client_perm_class(ClientAction.READ_APPLICATIONS)]

    def retrieve_related_applications_info(self, request, db_name):
        """查看 mysql 增强服务的数据库关联的应用信息

        APIGW 调用此接口,根据给定的 mysql 增强服务数据库名称(db_name)检索相关的应用信息。
        """
        store = get_remote_store()
        service_mgr = RemoteServiceMgr(store)
        services = service_mgr.get_mysql_services()
        for service in services:
            service_instance_mgr = RemoteServiceInstanceMgr(store, service)
            app = get_app_by_instance_name(service_instance_mgr, db_name)
            if app is None:
                continue
            return Response(ApplicationMembersInfoSLZ(app).data)
        return Response(status=status.HTTP_200_OK)
