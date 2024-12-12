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
import os
from pathlib import Path
from typing import Dict, List

import requests
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.dev_sandbox.constants import DevSandboxStatus
from paas_wl.bk_app.dev_sandbox.controller import DevSandboxController, DevSandboxWithCodeEditorController
from paas_wl.bk_app.dev_sandbox.entities import DevSandboxWithCodeEditorDetail
from paas_wl.bk_app.dev_sandbox.exceptions import DevSandboxAlreadyExists, DevSandboxResourceNotFound
from paasng.accessories.dev_sandbox.models import CodeEditor, DevSandbox, gen_dev_sandbox_code
from paasng.accessories.services.utils import generate_password
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.engine.configurations.config_var import get_env_variables
from paasng.platform.engine.utils.source import get_source_dir
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.constants import FileChangeType
from paasng.platform.sourcectl.exceptions import CallGitApiFailed
from paasng.platform.sourcectl.models import ChangedFile, CommitInfo, VersionInfo
from paasng.platform.sourcectl.repo_controller import get_repo_controller
from paasng.utils.error_codes import error_codes

from .config_var import CONTAINER_TOKEN_ENV, generate_envs
from .serializers import (
    CreateDevSandboxWithCodeEditorSLZ,
    DevSandboxCommitInputSLZ,
    DevSandboxCommitOutputSLZ,
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
        """部署开发沙箱

        FIXME（沙箱重构）这个函数太长了，职责不清晰，重构时需要做拆分
        """
        # 同时支持的开发沙箱数量是有上限的
        if DevSandbox.objects.count() >= settings.DEV_SANDBOX_COUNT_LIMIT:
            raise error_codes.DEV_SANDBOX_COUNT_OVER_LIMIT

        app = self.get_application()
        module = self.get_module_via_path()

        # 同一用户同一环境只能有一个运行中的沙箱
        if DevSandbox.objects.filter(owner=request.user.pk, module=module).exists():
            raise error_codes.DEV_SANDBOX_ALREADY_EXISTS

        # 目前仅支持 vcs 类型的源码获取方式
        if module.get_source_origin() != SourceOrigin.AUTHORIZED_VCS:
            raise error_codes.UNSUPPORTED_SOURCE_ORIGIN

        serializer = CreateDevSandboxWithCodeEditorSLZ(
            data=request.data, context={"module": module, "operator": request.user.pk}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        # 代码版本信息
        version_info = VersionInfo(
            version_type=data["version_type"],
            version_name=data["version_name"],
            revision=data["revision"],
        )

        dev_sandbox_code = gen_dev_sandbox_code()
        dev_sandbox = DevSandbox.objects.create(
            region=app.region,
            owner=request.user.pk,
            module=module,
            status=DevSandboxStatus.ACTIVE.value,
            version_info=version_info,
            code=dev_sandbox_code,
        )
        # 更新过期时间
        dev_sandbox.renew_expired_at()

        # 生成代码编辑器密码
        password = generate_password()
        CodeEditor.objects.create(dev_sandbox=dev_sandbox, password=password)

        controller = DevSandboxWithCodeEditorController(
            app=app,
            module_name=module.name,
            dev_sandbox_code=dev_sandbox.code,
            owner=request.user.pk,
        )
        try:
            # FIXME（沙箱重构）这里获取部署目录的逻辑过于冗余了，实际上无需考虑源码包的情况？
            # 获取构建目录相对路径
            source_dir = get_source_dir(module, request.user.pk, version_info)
            relative_source_dir = Path(source_dir)
            if relative_source_dir.is_absolute():
                logger.warning(
                    "Unsupported absolute path<%s>, force transform to relative_to path.", relative_source_dir
                )
                relative_source_dir = relative_source_dir.relative_to("/")

            # 获取环境变量（复用 stag 环境）
            envs = generate_envs(app, module)
            stag_envs = get_env_variables(module.get_envs(AppEnvironment.STAGING))
            envs.update(stag_envs)

            controller.deploy(
                dev_sandbox_env_vars=envs,
                code_editor_env_vars={},
                version_info=version_info,
                relative_source_dir=relative_source_dir,
                password=password,
            )
        except DevSandboxAlreadyExists:
            # FIXME（沙箱重构）为啥删除 model 不清理资源？
            # 开发沙箱已存在，只删除 model 对象，不删除沙箱资源
            dev_sandbox.delete()
            raise error_codes.DEV_SANDBOX_ALREADY_EXISTS
        except Exception:
            # 除了沙箱已存在的情况，其它创建异常情况下，清理沙箱资源
            controller.delete()
            dev_sandbox.delete()
            raise

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(responses={"204": "没有返回数据"})
    def delete(self, request, code, module_name):
        """清理开发沙箱"""
        app = self.get_application()
        module = self.get_module_via_path()

        try:
            dev_sandbox = DevSandbox.objects.get(owner=request.user.pk, module=module)
        except DevSandbox.DoesNotExist:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        controller = DevSandboxWithCodeEditorController(
            app=app,
            module_name=module.name,
            dev_sandbox_code=dev_sandbox.code,
            owner=request.user.pk,
        )
        controller.delete()
        dev_sandbox.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["开发沙箱"], Response={200: DevSandboxWithCodeEditorDetailSLZ})
    def get_detail(self, request, code, module_name):
        """获取开发沙箱的运行详情"""
        app = self.get_application()
        module = self.get_module_via_path()
        try:
            dev_sandbox = DevSandbox.objects.get(owner=request.user.pk, module=module)
        except DevSandbox.DoesNotExist:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        controller = DevSandboxWithCodeEditorController(
            app=app,
            module_name=module.name,
            dev_sandbox_code=dev_sandbox.code,
            owner=request.user.pk,
        )
        try:
            detail = controller.get_detail()
        except DevSandboxResourceNotFound:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        serializer = DevSandboxWithCodeEditorDetailSLZ(
            {
                "urls": detail.urls,
                # FIXME（沙箱重构）token 不应该从环境变量获取，建议重构时候加密存入 DevSandbox 表
                "token": detail.dev_sandbox_env_vars[CONTAINER_TOKEN_ENV],
                "dev_sandbox_status": detail.dev_sandbox_status,
                "code_editor_status": detail.code_editor_status,
                "dev_sandbox_env_vars": detail.dev_sandbox_env_vars,
            }
        )
        return Response(data=serializer.data)

    @swagger_auto_schema(tags=["开发沙箱"])
    def get_password(self, request, code, module_name):
        """验证验证码查看代码编辑器密码"""
        module = self.get_module_via_path()

        try:
            dev_sandbox = DevSandbox.objects.get(owner=request.user.pk, module=module)
        except DevSandbox.DoesNotExist:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        return Response({"password": dev_sandbox.code_editor.password})

    @swagger_auto_schema(tags=["开发沙箱"], Response={200: DevSandboxSLZ(many=True)})
    def list_app_dev_sandbox(self, request, code):
        """获取该应用下用户的开发沙箱"""
        app = self.get_application()
        modules = app.modules.all()
        dev_sandboxes = DevSandbox.objects.filter(owner=request.user.pk, module__in=modules)

        return Response(data=DevSandboxSLZ(dev_sandboxes, many=True).data)

    @swagger_auto_schema(tags=["开发沙箱"])
    def pre_deploy_check(self, request, code):
        """部署前确认是否可以部署"""
        # 判断开发沙箱数量是否超过限制
        if DevSandbox.objects.count() >= settings.DEV_SANDBOX_COUNT_LIMIT:
            return Response(data={"result": False})

        return Response(data={"result": True})


class DevSandboxCommitApi(generics.CreateAPIView, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(
        tags=["开发沙箱"],
        operation_description="提交变更的代码",
        request_body=DevSandboxCommitInputSLZ(),
        responses={status.HTTP_200_OK: DevSandboxCommitOutputSLZ()},
    )
    def post(self, request, *args, **kwargs):
        slz = DevSandboxCommitInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        app = self.get_application()
        module = self.get_module_via_path()
        operator = request.user.pk

        try:
            dev_sandbox = DevSandbox.objects.get(owner=operator, module=module)
        except DevSandbox.DoesNotExist:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        controller = DevSandboxWithCodeEditorController(
            app=app, module_name=module.name, dev_sandbox_code=dev_sandbox.code, owner=operator
        )
        try:
            detail = controller.get_detail()
        except DevSandboxResourceNotFound:
            raise error_codes.DEV_SANDBOX_NOT_FOUND

        # 1. 调用 devserver api 获取代码差异信息
        diffs = self._fetch_dev_sandbox_diffs(detail)
        # 2. 构建提交信息（CommitInfo）
        commit_info = self._build_commit_info(module, dev_sandbox, diffs, data["message"])
        # 3. 调用代码库 API 提交代码
        repo_url = self._commit_to_repository(module, dev_sandbox, operator, commit_info)
        # 4. 在沙箱中也进行一次 commit，否则无法重复提交
        self._commit_in_dev_sandbox(detail, data["message"])

        return Response(status=status.HTTP_200_OK, data=DevSandboxCommitOutputSLZ({"repo_url": repo_url}).data)

    @staticmethod
    def _fetch_dev_sandbox_diffs(detail: DevSandboxWithCodeEditorDetail) -> List[Dict]:
        """从沙箱获取代码变更文件"""
        # FIXME（沙箱重构）
        #  1. 这里的 devserver_url 其实只是个 host + prefix，没带 scheme 还以 / 结尾
        #  2. token 不应该从环境变量获取，建议重构时候加密存入 DevSandbox 表
        resp = requests.get(
            f"http://{detail.urls.devserver_url}diffs",
            headers={"Authorization": f"Bearer {detail.dev_sandbox_env_vars[CONTAINER_TOKEN_ENV]}"},
            params={"content": "true"},
        )
        if resp.status_code != status.HTTP_200_OK:
            raise error_codes.DEV_SANDBOX_API_ERROR.f(resp.text)

        resp_data = resp.json()
        if not resp_data["total"]:
            raise error_codes.CANNOT_COMMIT_TO_REPO.f("no diff files found")

        return resp_data["files"]

    @staticmethod
    def _build_commit_info(module: Module, dev_sandbox: DevSandbox, diffs: List[Dict], commit_msg: str) -> CommitInfo:
        """根据变更的文件构建提交信息"""
        # 代码部署目录
        source_dir = module.get_source_obj().get_source_dir()

        commit_info = CommitInfo(branch=dev_sandbox.version_info.version_name, message=commit_msg)
        mapping = {
            FileChangeType.ADDED: commit_info.add_files,
            FileChangeType.MODIFIED: commit_info.edit_files,
            FileChangeType.DELETED: commit_info.delete_files,
        }
        for item in diffs:
            path = os.path.join(source_dir, item["path"]) if source_dir else item["path"]
            mapping[item["action"]].append(ChangedFile(path, item["content"]))

        return commit_info

    @staticmethod
    def _commit_to_repository(module: Module, dev_sandbox: DevSandbox, operator: str, commit_info: CommitInfo) -> str:
        """提交代码到代码库"""
        repo_ctrl = get_repo_controller(module, operator)
        try:
            repo_ctrl.batch_commit_files(commit_info)
        except CallGitApiFailed as e:
            raise error_codes.CANNOT_COMMIT_TO_REPO.f(str(e))

        return repo_ctrl.build_url(dev_sandbox.version_info)

    @staticmethod
    def _commit_in_dev_sandbox(detail: DevSandboxWithCodeEditorDetail, commit_msg: str) -> None:
        """在沙箱本地执行一次 commit"""
        # FIXME（沙箱重构）同上
        resp = requests.get(
            f"http://{detail.urls.devserver_url}commit",
            headers={"Authorization": f"Bearer {detail.dev_sandbox_env_vars[CONTAINER_TOKEN_ENV]}"},
            params={"message": commit_msg},
        )
        if resp.status_code != status.HTTP_200_OK:
            raise error_codes.DEV_SANDBOX_API_ERROR.f(resp.text)
