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
from pathlib import Path
from typing import Dict

from bkpaas_auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.dev_sandbox.constants import CodeEditorStatus
from paas_wl.bk_app.dev_sandbox.controller import DevSandboxController, DevSandboxWithCodeEditorController
from paas_wl.bk_app.dev_sandbox.exceptions import DevSandboxAlreadyExists, DevSandboxResourceNotFound
from paasng.accessories.dev_sandbox.models import CodeEditor, DevSandbox
from paasng.accessories.services.utils import generate_password
from paasng.infras.accounts.constants import FunctionType
from paasng.infras.accounts.models import make_verifier
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.accounts.serializers import VerificationCodeSLZ
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.engine.configurations.config_var import get_env_variables
from paasng.platform.engine.utils.source import get_source_dir
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models.module import Module
from paasng.platform.sourcectl.exceptions import GitLabBranchNameBugError
from paasng.platform.sourcectl.models import VersionInfo
from paasng.platform.sourcectl.version_services import get_version_service
from paasng.utils.error_codes import error_codes

from .config_var import CONTAINER_TOKEN_ENV, generate_envs
from .serializers import (
    CreateDevSandboxWithCodeEditorSLZ,
    DevSandboxDetailSLZ,
    DevSandboxSLZ,
    DevSandboxWithCodeEditorDetailSLZ,
)

logger = logging.getLogger(__name__)


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


class DevSandboxWithCodeEditorViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(request_body=CreateDevSandboxWithCodeEditorSLZ, responses={"201": "没有返回数据"})
    def deploy(self, request, code, module_name):
        """部署开发沙箱"""
        app = self.get_application()
        module = self.get_module_via_path()

        if DevSandbox.objects.filter(owner=request.user.pk, module=module).exists():
            raise error_codes.DEV_SANDBOX_ALREADY_EXISTS

        controller = DevSandboxWithCodeEditorController(
            app=app,
            module_name=module.name,
            owner=request.user,
        )

        serializer = CreateDevSandboxWithCodeEditorSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.data

        # 仅支持 vcs 类型的源码获取方式
        source_origin = module.get_source_origin()
        if source_origin != SourceOrigin.AUTHORIZED_VCS:
            raise error_codes.UNSUPPORTED_SOURCE_ORIGIN

        # 获取版本信息
        version_info = self._get_version_info(request.user, module, params)

        # 获取构建目录相对路径
        source_dir = get_source_dir(module, request.user.pk, version_info)
        relative_source_dir = Path(source_dir)
        if relative_source_dir.is_absolute():
            logger.warning("Unsupported absolute path<%s>, force transform to relative_to path.", relative_source_dir)
            relative_source_dir = relative_source_dir.relative_to("/")

        # 生成密码
        password = generate_password()

        # 获取环境变量（复用 stag 环境）
        envs = generate_envs(app, module)
        stag_envs = get_env_variables(module.get_envs("stag"))
        envs.update(stag_envs)

        try:
            controller.deploy(
                dev_sandbox_env_vars=envs,
                code_editor_env_vars={},
                version_info=version_info,
                relative_source_dir=relative_source_dir,
                password=password,
            )
        except DevSandboxAlreadyExists:
            raise error_codes.DEV_SANDBOX_ALREADY_EXISTS

        dev_sandbox = DevSandbox.objects.create(
            region=app.region,
            owner=request.user.pk,
            module=module,
            status=CodeEditorStatus.ALIVE.value,
            version_info=version_info,
        )

        CodeEditor.objects.create(
            dev_sandbox=dev_sandbox,
            password=password,
        )

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(responses={"204": "没有返回数据"})
    def delete(self, request, code, module_name):
        """清理开发沙箱"""
        app = self.get_application()
        module = self.get_module_via_path()
        controller = DevSandboxWithCodeEditorController(
            app=app,
            module_name=module.name,
            owner=request.user,
        )
        controller.delete()

        try:
            DevSandbox.objects.get(owner=request.user.pk, module=module).delete()
        except DevSandbox.DoesNotExist:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["开发沙箱"], Response={200: DevSandboxWithCodeEditorDetailSLZ})
    def get_detail(self, request, code, module_name):
        """获取开发沙箱的运行详情"""
        app = self.get_application()
        module = self.get_module_via_path()
        if not DevSandbox.objects.filter(owner=request.user.pk, module=module).exists():
            raise error_codes.DEV_SANDBOX_NOT_FOUND
        controller = DevSandboxWithCodeEditorController(
            app=app,
            module_name=module.name,
            owner=request.user,
        )
        try:
            detail = controller.get_detail()
        except DevSandboxResourceNotFound:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        serializer = DevSandboxWithCodeEditorDetailSLZ(
            {
                "urls": detail.urls,
                "token": detail.dev_sandbox_env_vars[CONTAINER_TOKEN_ENV],
                "dev_sandbox_status": detail.dev_sandbox_status,
                "code_editor_status": detail.code_editor_status,
                "dev_sandbox_env_vars": detail.dev_sandbox_env_vars,
            }
        )
        return Response(data=serializer.data)

    @swagger_auto_schema(tags=["鉴权信息"], request_body=VerificationCodeSLZ)
    def get_password(self, request, code, module_name):
        """验证验证码查看代码编辑器密码"""
        module = self.get_module_via_path()

        try:
            dev_sandbox = DevSandbox.objects.get(owner=request.user.pk, module=module)
        except DevSandbox.DoesNotExist:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        # 部分版本没有发送通知的渠道可置：跳过验证码校验步骤
        if settings.ENABLE_VERIFICATION_CODE:
            serializer = VerificationCodeSLZ(data=request.data)
            serializer.is_valid(raise_exception=True)

            verifier = make_verifier(request.session, FunctionType.GET_CODE_EDITOR_PASSWORD.value)
            is_valid = verifier.validate(serializer.data["verification_code"])
            if not is_valid:
                raise ValidationError({"verification_code": [_("验证码错误")]})
        else:
            logger.warning("Verification code is not currently supported, return app secret directly")

        return Response({"password": dev_sandbox.code_editor.password})

    @swagger_auto_schema(tags=["开发沙箱"], Response={200: DevSandboxWithCodeEditorDetailSLZ})
    def list_app_dev_sandbox(self, request, code):
        """获取该应用下用户的开发沙箱"""
        app = self.get_application()
        modules = app.modules.all()
        dev_sandboxes = DevSandbox.objects.filter(owner=request.user.pk, module__in=modules)

        return Response(data=DevSandboxSLZ(dev_sandboxes, many=True).data)

    @staticmethod
    def _get_version_info(user: User, module: Module, params: Dict) -> VersionInfo:
        """Get VersionInfo from user inputted params"""
        version_name = params["version_name"]
        version_type = params["version_type"]
        revision = params.get("revision")
        try:
            # 尝试根据获取最新的 revision
            version_service = get_version_service(module, operator=user.pk)
            revision = version_service.extract_smart_revision(f"{version_type}:{version_name}")
        except GitLabBranchNameBugError as e:
            raise error_codes.CANNOT_GET_REVISION.f(str(e))
        except NotImplementedError:
            logger.debug(
                "The current source code system does not support parsing the version unique ID from the version name"
            )
        except Exception:
            logger.exception("Failed to parse version information.")

        # 如果前端没有提供 revision 信息, 就报错
        if not revision:
            raise error_codes.CANNOT_GET_REVISION
        return VersionInfo(revision, version_name, version_type)
