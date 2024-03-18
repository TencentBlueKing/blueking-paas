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
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.dev_sandbox.controller import DevSandboxController
from paas_wl.bk_app.dev_sandbox.exceptions import DevSandboxAlreadyExists, DevSandboxResourceNotFound
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes

from .config_var import CONTAINER_TOKEN_ENV, generate_envs
from .serializers import DevSandboxDetailSLZ


class DevSandboxViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(tags=["开发沙箱"], responses={"201": "没有返回数据"})
    def deploy(self, request, **kwargs):
        """部署开发沙箱"""
        app = self.get_application()
        module = self.get_module_via_path()

        controller = DevSandboxController(app, module.name)
        try:
            controller.deploy(envs=generate_envs(app, module))
        except DevSandboxAlreadyExists:
            raise error_codes.DEV_SANDBOX_ALREADY_EXISTS

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["开发沙箱"], responses={"204": "没有返回数据"})
    def delete(self, request, code, module_name):
        """清理开发沙箱"""
        controller = DevSandboxController(self.get_application(), module_name)
        controller.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["开发沙箱"], Response={200: DevSandboxDetailSLZ})
    def get_detail(self, request, code, module_name):
        """获取开发沙箱的运行详情"""
        controller = DevSandboxController(self.get_application(), module_name)
        try:
            detail = controller.get_sandbox_detail()
        except DevSandboxResourceNotFound:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        serializer = DevSandboxDetailSLZ(
            {"url": detail.url, "token": detail.envs[CONTAINER_TOKEN_ENV], "status": detail.status}
        )
        return Response(data=serializer.data)
