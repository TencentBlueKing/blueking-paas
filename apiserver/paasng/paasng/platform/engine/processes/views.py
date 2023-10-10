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

from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN

from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.processes.shim import ProcessManager
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.accessories.serializers import DocumentaryLinkSLZ
from paasng.accessories.smart_advisor.advisor import DocumentaryLinkAdvisor
from paasng.accessories.smart_advisor.tags import get_dynamic_tag
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.accounts.permissions.user import user_has_feature
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.processes import serializers as slzs
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.misc.feature_flags.constants import PlatformFeatureFlag as PFF
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.platform.modules.models import AppSlugRunner
from paasng.platform.modules.specs import ModuleSpecs
from paasng.utils.error_codes import error_codes

# Create your views here.

logger = logging.getLogger(__name__)


class ApplicationProcessWebConsoleViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [
        IsAuthenticated,
        application_perm_class(AppAction.BASIC_DEVELOP),
    ]

    def _is_whitelisted_user(self, request):
        return user_has_feature(AFF.ENABLE_WEB_CONSOLE)().has_permission(request, self)

    def _is_cloud_native_app(self, application):
        return application.type == ApplicationType.CLOUD_NATIVE

    def _is_s_mart_app(self, module):
        return module.get_source_origin() == SourceOrigin.S_MART

    def _is_buildpack_app(self, module):
        return ModuleSpecs(module).runtime_type == RuntimeType.BUILDPACK

    @swagger_auto_schema(
        query_serializer=slzs.WebConsoleOpenSLZ, responses={200: slzs.WebConsoleResultSLZ}, tags=["获取控制台入口"]
    )
    def open(self, request, code, module_name, environment, process_type, process_instance_name):
        slz = slzs.WebConsoleOpenSLZ(data=request.query_params)
        slz.is_valid(True)

        application = self.get_application()
        module = self.get_module_via_path()
        env = self.get_env_via_path()
        manager = ProcessManager(env)

        if not PFF.get_default_flags()[PFF.ENABLE_WEB_CONSOLE]:
            # 平台不支持 WebConsole 功能
            raise error_codes.FEATURE_FLAG_DISABLED

        if self._is_whitelisted_user(request) or self._is_cloud_native_app(application) or self._is_s_mart_app(module):
            logger.debug("Allow to open the WebConsole")
        elif ModuleSpecs(module).runtime_type == RuntimeType.BUILDPACK:
            try:
                image = manager.get_running_image()
            except RuntimeError as e:
                raise error_codes.CANNOT_OPERATE_PROCESS.format(str(e))

            is_encrypted_image = any(
                runner.get_label(ModuleRuntimeManager.SECURE_ENCRYPTED_LABEL)
                # 升级镜像时会导致旧镜像无法打开 web-console (因为镜像的全名发生了变化)
                # 解决方案: 到管理端创建与旧镜像信息一样的隐藏镜像
                for runner in AppSlugRunner.objects.filter_by_full_image(module, image, contain_hidden=True)
            )
            if not is_encrypted_image:
                tag = get_dynamic_tag("app-feature:web-console")
                links = DocumentaryLinkAdvisor().search_by_tags([tag])
                if not links:
                    # 如果数据库无文章记录, 就只能抛异常了
                    raise error_codes.CANNOT_OPERATE_PROCESS.f(_("当前运行镜像不支持 WebConsole 功能，请尝试绑定最新运行时"))
                link = links[0]

                return Response(
                    data=DocumentaryLinkSLZ(link).data,
                    status=HTTP_403_FORBIDDEN,
                )

        # 云原生应用、镜像应用使用等非平台指定的镜像，使用 sh 命令
        command = "sh" if self._is_cloud_native_app(application) or self._is_s_mart_app(module) else "bash"
        try:
            result = manager.create_webconsole(
                request.user.username,
                process_type,
                process_instance_name,
                slz.validated_data.get("container_name"),
                command,
            )
        except AppEntityNotFound:
            raise error_codes.ERROR_UPDATING_PROC_SERVICE.f('未找到服务')

        data = result.get("data") or {}
        return Response(
            {
                "code": result.get("code"),
                "message": result.get("message"),
                "request_id": result.get("request_id"),
                "session_id": data.get("session_id"),
                "web_console_url": data.get("web_console_url"),
            }
        )
