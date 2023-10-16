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
import json
import logging

import yaml
from django.http.response import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.bk_app.cnative.specs.constants import ACCESS_CONTROL_ANNO_KEY, BKPAAS_ADDONS_ANNO_KEY
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.cnative.bkapp_model.manifest import get_manifest
from paasng.platform.cnative.serializers import GetManifestInputSLZ

logger = logging.getLogger(__name__)


# TODO: Remove this API entirely because if become stale
class CNativeAppManifestExtViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """云原生应用扩展信息管理"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def retrieve(self, request, code, module_name, environment):
        """提供应用扩展信息，主要来源为平台扩展功能，如增强服务配置等"""
        engine_app = self.get_engine_app_via_path()
        # 只要绑定即可用于展示，不关心是否已经分配实例
        service_names = [svc.name for svc in mixed_service_mgr.list_binded(engine_app.env.module)]
        manifest_ext = {"metadata": {"annotations": {BKPAAS_ADDONS_ANNO_KEY: json.dumps(service_names)}}}

        try:
            from paasng.security.access_control.models import ApplicationAccessControlSwitch
        except ImportError:
            logger.info('access control only supported in te region, skip...')
        else:
            if ApplicationAccessControlSwitch.objects.is_enabled(self.get_application()):
                manifest_ext["metadata"]["annotations"][ACCESS_CONTROL_ANNO_KEY] = "true"

        return Response(data=manifest_ext)


class BkAppModelManifestsViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """The main viewset for managing the manifests of blueking application model."""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(query_serializer=GetManifestInputSLZ, tags=["云原生应用"])
    def retrieve(self, request, code, module_name):
        """获取当前模块的蓝鲸应用模型数据，支持 JSON、YAML 等不同格式。"""
        slz = GetManifestInputSLZ(data=request.GET)
        slz.is_valid(raise_exception=True)
        module = self.get_module_via_path()

        output_format = slz.validated_data['output_format']
        if output_format == 'yaml':
            manifests = get_manifest(module)
            response = yaml.safe_dump_all(manifests)
            # Use django's response to ignore DRF's renders
            return HttpResponse(response, content_type='application/yaml')
        else:
            return Response(get_manifest(module))
