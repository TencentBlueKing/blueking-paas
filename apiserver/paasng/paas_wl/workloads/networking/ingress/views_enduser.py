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

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.constants import MODULE_NAME_ANNO_KEY
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.networking.ingress.kres_entities.service import service_kmodel
from paas_wl.workloads.networking.ingress.managers.misc import AppDefaultIngresses, LegacyAppIngressMgr
from paas_wl.workloads.networking.ingress.serializers import ProcIngressSLZ, ProcServiceSLZ
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class ProcessServicesViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """管理应用内部服务相关 API"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def list(self, request, code, module_name, environment):
        """查看所有进程服务信息"""
        env = self.get_env_via_path()
        wl_app = WlApp.objects.get(pk=env.engine_app_id)

        # Get all services
        labels = None
        if wl_app.type == WlAppType.CLOUD_NATIVE:
            labels = {MODULE_NAME_ANNO_KEY: wl_app.module_name}

        proc_services = service_kmodel.list_by_app(wl_app, labels)
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
