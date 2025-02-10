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

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.dev_sandbox.constants import SourceCodeFetchMethod
from paas_wl.bk_app.dev_sandbox.controller import DevSandboxController
from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig, SourceCodeConfig
from paas_wl.bk_app.dev_sandbox.exceptions import DevSandboxAlreadyExists, DevSandboxResourceNotFound
from paasng.accessories.dev_sandbox.commit import DevSandboxCodeCommit
from paasng.accessories.dev_sandbox.config_var import generate_envs
from paasng.accessories.dev_sandbox.exceptions import CannotCommitToRepository, DevSandboxApiException
from paasng.accessories.dev_sandbox.models import CodeEditor, DevSandbox
from paasng.accessories.dev_sandbox.serializers import (
    DevSandboxCommitInputSLZ,
    DevSandboxCommitOutputSLZ,
    DevSandboxCreateInputSLZ,
    DevSandboxCreateOutputSLZ,
    DevSandboxListOutputSLZ,
    DevSandboxPreDeployCheckOutputSLZ,
    DevSandboxRetrieveOutputSLZ,
)
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.engine.utils.source import get_source_dir, upload_source_code
from paasng.platform.modules.constants import SourceOrigin
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class DevSandboxViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """开发沙箱"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    lookup_field = "code"
    lookup_url_kwarg = "dev_sandbox_code"

    def get_queryset(self):
        module = self.get_module_via_path()
        return DevSandbox.objects.filter(module=module, owner=self.request.user.pk)

    @swagger_auto_schema(
        tags=["accessories.dev_sandbox"],
        operation_description="获取应用所有模块的开发沙箱列表",
        responses={status.HTTP_200_OK: DevSandboxListOutputSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        modules = self.get_application().modules.all()
        dev_sandboxes = DevSandbox.objects.filter(owner=request.user.pk, module__in=modules)
        return Response(data=DevSandboxListOutputSLZ(dev_sandboxes, many=True).data)

    @swagger_auto_schema(
        tags=["accessories.dev_sandbox"],
        operation_description="创建开发沙箱",
        request_body=DevSandboxCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: DevSandboxCreateOutputSLZ()},
    )
    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        # 限制开发沙箱的总数量
        if DevSandbox.objects.count() >= settings.DEV_SANDBOX_COUNT_LIMIT:
            raise error_codes.DEV_SANDBOX_COUNT_OVER_LIMIT

        module = self.get_module_via_path()

        slz = DevSandboxCreateInputSLZ(
            data=request.data,
            context={"module": module, "operator": request.user.pk},
        )
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        # 同用户同模块只能有一个运行中的沙箱
        owner = request.user.pk
        if DevSandbox.objects.filter(owner=owner, module=module).exists():
            raise error_codes.DEV_SANDBOX_ALREADY_EXISTS

        # 目前仅支持 vcs 类型的源码获取方式
        if module.get_source_origin() != SourceOrigin.AUTHORIZED_VCS:
            raise error_codes.UNSUPPORTED_SOURCE_ORIGIN

        version_info = data.get("source_code_version_info")
        # 默认为 HTTP 文件提供源代码
        source_code_cfg = SourceCodeConfig(source_fetch_method=SourceCodeFetchMethod.HTTP)
        # 如果已经指定代码配置，则需要修改配置
        if version_info:
            source_dir = get_source_dir(module, owner, version_info)
            source_code_cfg.source_fetch_url = upload_source_code(module, version_info, source_dir, owner)
            source_code_cfg.source_fetch_method = SourceCodeFetchMethod.BK_REPO

        dev_sandbox = DevSandbox.objects.create(module=module, version_info=version_info, owner=owner)
        # 代码编辑器
        code_editor_cfg: CodeEditorConfig | None = None
        if data["enable_code_editor"]:
            code_editor = CodeEditor.objects.create(dev_sandbox=dev_sandbox)
            code_editor_cfg = CodeEditorConfig(password=code_editor.password)

        # 下发沙箱 k8s 资源
        try:
            DevSandboxController(module, dev_sandbox.code).deploy(
                envs=generate_envs(module),
                source_code_cfg=source_code_cfg,
                code_editor_cfg=code_editor_cfg,
            )
        except DevSandboxAlreadyExists:
            raise error_codes.DEV_SANDBOX_ALREADY_EXISTS
        except Exception:
            logger.exception("Failed to deploy dev sandbox")
            dev_sandbox.delete()
            raise error_codes.DEV_SANDBOX_CREATE_FAILED

        return Response(data=DevSandboxCreateOutputSLZ(dev_sandbox), status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["accessories.dev_sandbox"],
        operation_description="获取开发沙箱详情",
        responses={status.HTTP_200_OK: DevSandboxRetrieveOutputSLZ()},
    )
    def retrieve(self, request, *args, **kwargs):
        module = self.get_module_via_path()
        dev_sandbox = self.get_object()

        try:
            detail = DevSandboxController(module, dev_sandbox.code).get_detail()
        except DevSandboxResourceNotFound:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        try:
            password = dev_sandbox.code_editor.password
        except ObjectDoesNotExist:
            password = None

        resp_data = {
            "urls": detail.urls,
            "devserver_token": dev_sandbox.token,
            "code_editor_password": password,
        }
        return Response(data=DevSandboxRetrieveOutputSLZ(resp_data).data)

    @swagger_auto_schema(
        tags=["accessories.dev_sandbox"],
        operation_description="删除开发沙箱",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, *args, **kwargs):
        module = self.get_module_via_path()
        dev_sandbox = self.get_object()

        # 清理集群中的沙箱资源
        controller = DevSandboxController(module, dev_sandbox.code)
        controller.delete()
        # 删除开发沙箱实例
        dev_sandbox.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["accessories.dev_sandbox"],
        operation_description="提交变更的代码",
        request_body=DevSandboxCommitInputSLZ(),
        responses={status.HTTP_200_OK: DevSandboxCommitOutputSLZ()},
    )
    def commit(self, request, *args, **kwargs):
        slz = DevSandboxCommitInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        module = self.get_module_via_path()
        operator = request.user.pk

        # 初始化提交器
        try:
            commitor = DevSandboxCodeCommit(module, operator)
        except (ObjectDoesNotExist, DevSandboxResourceNotFound):
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        # 沙箱代码提交
        try:
            repo_url = commitor.commit(data["message"])
        except DevSandboxApiException as e:
            raise error_codes.DEV_SANDBOX_API_ERROR.f(str(e))
        except CannotCommitToRepository as e:
            raise error_codes.CANNOT_COMMIT_TO_REPOSITORY.f(str(e))

        return Response(
            status=status.HTTP_200_OK,
            data=DevSandboxCommitOutputSLZ({"repo_url": repo_url}).data,
        )

    @swagger_auto_schema(
        tags=["accessories.dev_sandbox"],
        operation_description="部署前确认是否可以部署",
        responses={status.HTTP_200_OK: DevSandboxPreDeployCheckOutputSLZ()},
    )
    def pre_deploy_check(self, request, *args, **kwargs):
        # 判断开发沙箱数量是否超过限制
        result = bool(DevSandbox.objects.count() >= settings.DEV_SANDBOX_COUNT_LIMIT)
        return Response(data=DevSandboxPreDeployCheckOutputSLZ({"result": result}).data)
