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
from rest_framework.viewsets import ViewSet

from paas_wl.apis.admin.serializers.logs import ModuleEnvLogsConfigSLZ
from paasng.infras.accounts.permissions.global_site import SiteAction, site_perm_class
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin


class AppLogConfigViewSet(ViewSet, ApplicationCodeInPathMixin):
    """管理应用日志采集配置的 ViewSet"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    @swagger_auto_schema(response_serializer=ModuleEnvLogsConfigSLZ(many=True), tags=["Logs"])
    def list(self, request, **kwargs):
        """查看应用所有环境的日志采集配置

        结果默认按（“模块名”、“环境”）排序
        """
        application = self.get_application()
        data = []
        for module in application.modules.all():
            for env in module.get_envs():
                wl_app = env.wl_app
                config = wl_app.latest_config
                data.append(
                    {
                        "module_name": module.name,
                        "environment": env.environment,
                        "mount_log_to_host": config.mount_log_to_host,
                    }
                )

        return Response(ModuleEnvLogsConfigSLZ(data, many=True).data)

    @swagger_auto_schema(request_body=ModuleEnvLogsConfigSLZ, tags=["Logs"])
    def toggle(self, request, code):
        """修改某个环境是否允许挂载日志到宿主机"""
        slz = ModuleEnvLogsConfigSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        application = self.get_application()
        module = application.get_module(data["module_name"])
        env = module.get_envs(data["environment"])
        wl_app = env.wl_app
        config = wl_app.latest_config
        config.mount_log_to_host = data["mount_log_to_host"]
        config.save(update_fields=["mount_log_to_host", "updated"])
        return Response(status=status.HTTP_204_NO_CONTENT)
