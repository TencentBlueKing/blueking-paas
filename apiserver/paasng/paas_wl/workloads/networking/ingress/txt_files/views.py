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

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.workloads.networking.ingress.models import TxtFile
from paas_wl.workloads.networking.ingress.txt_files.serializers import TxtFileListSLZ, TxtFileSLZ
from paas_wl.workloads.networking.ingress.txt_files.sync import (
    get_served_hosts,
    is_txt_files_supported,
    sync_txt_file_ingresses,
)
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import ModuleEnvironment
from paasng.utils.api_docs import openapi_empty_response
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class TxtFilesViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """管理由平台在入口层直接返回的 txt 校验文件，仅支持云原生应用"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(response_serializer=TxtFileListSLZ, tags=["访问入口"])
    def list(self, request, code, module_name, environment):
        """查看环境的 txt 校验文件，supported 为 false 时表示环境只有子路径域名，配置不会生效"""
        env = self._get_env()
        data = {
            "supported": is_txt_files_supported(env),
            "hosts": get_served_hosts(env),
            "files": TxtFile.objects.filter(environment_id=env.id).order_by("id"),
        }
        return Response(TxtFileListSLZ(data).data)

    @swagger_auto_schema(request_body=TxtFileSLZ, response_serializer=TxtFileSLZ, tags=["访问入口"])
    def create(self, request, code, module_name, environment):
        """新建 txt 校验文件，保存后立即生效"""
        env = self._get_env()
        slz = TxtFileSLZ(data=request.data, context={"env": env, "served_hosts": get_served_hosts(env)})
        slz.is_valid(raise_exception=True)

        with transaction.atomic(using="workloads"):
            txt_file = slz.save(environment_id=env.id, tenant_id=env.application.tenant_id, operator=request.user.pk)
            self._sync(env)

        data = TxtFileSLZ(txt_file).data
        self._add_audit_record(request, env, OperationEnum.CREATE, f"{txt_file.host}{txt_file.path}", data_after=data)
        return Response(data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(request_body=TxtFileSLZ, response_serializer=TxtFileSLZ, tags=["访问入口"])
    def update(self, request, code, module_name, environment, id):
        """修改 txt 校验文件"""
        env = self._get_env()
        txt_file = get_object_or_404(TxtFile, environment_id=env.id, pk=id)
        data_before = TxtFileSLZ(txt_file).data
        slz = TxtFileSLZ(txt_file, data=request.data, context={"env": env, "served_hosts": get_served_hosts(env)})
        slz.is_valid(raise_exception=True)

        with transaction.atomic(using="workloads"):
            txt_file = slz.save(operator=request.user.pk)
            self._sync(env)

        data = TxtFileSLZ(txt_file).data
        self._add_audit_record(
            request,
            env,
            OperationEnum.MODIFY,
            f"{txt_file.host}{txt_file.path}",
            data_before=data_before,
            data_after=data,
        )
        return Response(data)

    @swagger_auto_schema(responses={204: openapi_empty_response}, tags=["访问入口"])
    def destroy(self, request, code, module_name, environment, id):
        """删除 txt 校验文件"""
        env = self._get_env()
        txt_file = get_object_or_404(TxtFile, environment_id=env.id, pk=id)
        data_before = TxtFileSLZ(txt_file).data

        with transaction.atomic(using="workloads"):
            txt_file.delete()
            self._sync(env)

        self._add_audit_record(
            request, env, OperationEnum.DELETE, f"{txt_file.host}{txt_file.path}", data_before=data_before
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_env(self) -> ModuleEnvironment:
        if self.get_application().type != ApplicationType.CLOUD_NATIVE:
            raise error_codes.TXT_FILE_UNSUPPORTED
        return self.get_env_via_path()

    @staticmethod
    def _sync(env: ModuleEnvironment):
        try:
            sync_txt_file_ingresses(env)
        except Exception:
            logger.exception("Failed to sync txt file ingresses for env %s", env)
            raise error_codes.SYNC_TXT_FILE_FAILED

    @staticmethod
    def _add_audit_record(
        request, env: ModuleEnvironment, operation: OperationEnum, path: str, data_before=None, data_after=None
    ):
        add_app_audit_record(
            app_code=env.application.code,
            tenant_id=env.application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=operation,
            target=OperationTarget.TXT_FILE,
            attribute=path,
            module_name=env.module.name,
            environment=env.environment,
            data_before=DataDetail(data=data_before) if data_before else None,
            data_after=DataDetail(data=data_after) if data_after else None,
        )
