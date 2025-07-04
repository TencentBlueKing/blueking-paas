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
from contextlib import suppress
from urllib.parse import quote

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from moby_distribution.registry.exceptions import AuthFailed, PermissionDeny, ResourceNotFound
from moby_distribution.registry.utils import parse_image
from rest_framework import status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.cnative.specs.constants import ResQuotaPlan
from paas_wl.bk_app.cnative.specs.exceptions import GetSourceConfigDataError
from paas_wl.bk_app.cnative.specs.models import AppModelRevision, Mount
from paas_wl.bk_app.cnative.specs.mounts import (
    MountManager,
    check_persistent_storage_enabled,
    check_storage_class_exists,
    init_volume_source_controller,
)
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP, PLAN_TO_REQUEST_QUOTA_MAP
from paas_wl.bk_app.cnative.specs.serializers import (
    AppModelRevisionSerializer,
    CreateMountSourceSLZ,
    DeleteMountSourcesSLZ,
    MountSLZ,
    MountSourceSLZ,
    QueryMountSourcesSLZ,
    QueryMountsSLZ,
    ResQuotaPlanSLZ,
    UpdateMountSourceSLZ,
    UpsertMountSLZ,
)
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.images.models import AppUserCredential
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.modules.models import BuildConfig
from paasng.platform.sourcectl.controllers.docker import DockerRegistryController
from paasng.platform.sourcectl.serializers import AlternativeVersionSLZ

logger = logging.getLogger(__name__)


class ResQuotaPlanOptionsView(APIView):
    """资源配额方案 选项视图"""

    @swagger_auto_schema(response_serializer=ResQuotaPlanSLZ(many=True))
    def get(self, request):
        return Response(
            data=ResQuotaPlanSLZ(
                [
                    {
                        "name": ResQuotaPlan.get_choice_label(plan),
                        "value": str(plan),
                        "limit": PLAN_TO_LIMIT_QUOTA_MAP[plan],
                        "request": PLAN_TO_REQUEST_QUOTA_MAP[plan],
                    }
                    for plan in ResQuotaPlan.get_values()
                ],
                many=True,
            ).data
        )


class MresVersionViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """应用资源版本相关视图"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={"200": AppModelRevisionSerializer})
    def retrieve(self, request, code, module_name, environment, revision_id):
        """获取某个已部署资源版本的详细信息，通常用于查看“部署历史”时，获取详细的 YAML 内容。"""
        try:
            revision = AppModelRevision.objects.get(pk=revision_id)
        except AppModelRevision.DoesNotExist:
            raise error_codes.GET_DEPLOYMENT_FAILED.f(f"app model revision id {revision_id} not found")
        return Response(AppModelRevisionSerializer(revision).data)


class ImageRepositoryView(GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def _validate_registry_permission(self, registry_service: DockerRegistryController):
        """Validates the registry permission by attempting to touch it.

        :raise: error_codes.INVALID_CREDENTIALS: If the credentials are invalid or the repository is unreachable.
        """
        with suppress(Exception):
            # bkrepo 的 docker 仓库，镜像凭证没有填写正确时，.touch() 时会抛出异常
            if registry_service.touch():
                return
            raise error_codes.LIST_TAGS_FAILED.f(_("权限不足或仓库不可达"))

    @swagger_auto_schema(response_serializer=AlternativeVersionSLZ(many=True))
    def list_tags(self, request, code, module_name):
        """列举 bkapp 声明的镜像仓库中的所有 tag, 仅支持 v1alpha2 版本的云原生应用"""
        application = self.get_application()
        module = self.get_module_via_path()

        cfg = BuildConfig.objects.get_or_create_by_module(module)
        if not cfg.image_repository:
            raise error_codes.LIST_TAGS_FAILED.f("no image_repository found")

        # 如果用户填的是 dockerhub 的镜像仓库，则补齐 registry 的域名信息
        parsed = parse_image(cfg.image_repository, default_registry="index.docker.io")
        repository = f"{parsed.domain}/{parsed.name}"
        credential_name = cfg.image_credential_name

        username, password = "", ""
        if credential_name:
            try:
                credential = AppUserCredential.objects.get(application_id=application.id, name=credential_name)
            except AppUserCredential.DoesNotExist:
                raise error_codes.INVALID_CREDENTIALS.f(_("镜像凭证不存在"))
            username, password = credential.username, credential.password

        endpoint, slash, repo = repository.partition("/")
        registry_service = DockerRegistryController(endpoint=endpoint, repo=repo, username=username, password=password)

        self._validate_registry_permission(registry_service)

        try:
            alternative_versions = AlternativeVersionSLZ(registry_service.list_alternative_versions(), many=True).data
        except ResourceNotFound:
            raise error_codes.LIST_TAGS_FAILED.f(_("镜像仓库不存在，请检查仓库地址是否正确"), replace=True)
        except PermissionDeny:
            raise error_codes.INVALID_CREDENTIALS.f(_("镜像仓库权限不足, 请检查是否配置镜像凭证"), replace=True)
        except AuthFailed:
            raise error_codes.INVALID_CREDENTIALS.f(_("镜像仓库凭证错误, 请检查镜像凭证配置是否正确"), replace=True)
        except requests.exceptions.Timeout:
            raise error_codes.LIST_TAGS_FAILED.f(_("镜像仓库请求超时, 请检查网络连接"), replace=True)
        except Exception:
            if endpoint == "mirrors.tencent.com":
                # 镜像源迁移期间不能保证 registry 所有接口可用, 迁移期间增量镜像仓库无法查询 tag
                # TODO: 当镜像源迁移完成后移除该代码
                project_name, slash, repo_name = repo.partition("/")
                raise error_codes.LIST_TAGS_FAILED.set_data(
                    {
                        "tips": _("查看镜像 Tag"),
                        "url": "https://mirrors.tencent.com/#/private/docker/detail"
                        "?project_name={project_name}&repo_name={repo_name}".format(
                            project_name=quote(project_name, safe=""), repo_name=quote(repo_name, safe="")
                        ),
                    }
                )
            logger.exception("unable to fetch repo info, may be the credential error or a network exception.")
            raise error_codes.LIST_TAGS_FAILED.f(_("拉取镜像 Tag 失败"), replace=True)
        return Response(data=alternative_versions)


class VolumeMountViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]
    pagination_class = LimitOffsetPagination

    @swagger_auto_schema(query_serializer=QueryMountsSLZ, responses={200: MountSLZ(many=True)})
    def list(self, request, code, module_name):
        module = self.get_module_via_path()

        slz = QueryMountsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data

        mounts = Mount.objects.filter(module_id=module.id).order_by("-created")

        # Filter by environment_name if provided
        environment_name = params.get("environment_name")
        if environment_name:
            mounts = mounts.filter(environment_name=environment_name)
        # Filter by source_type if provided
        source_type = params.get("source_type")
        if source_type:
            mounts = mounts.filter(source_type=source_type)

        page = self.paginator.paginate_queryset(mounts, self.request, view=self)
        try:
            slz = MountSLZ(page, many=True)
        except GetSourceConfigDataError as e:
            raise error_codes.LIST_VOLUME_MOUNTS_FAILED.f(_(e))

        return self.paginator.get_paginated_response(slz.data)

    @transaction.atomic
    @swagger_auto_schema(responses={201: MountSLZ()}, request_body=UpsertMountSLZ)
    def create(self, request, code, module_name):
        application = self.get_application()
        module = self.get_module_via_path()
        slz = UpsertMountSLZ(data=request.data, context={"module_id": module.id})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        # 创建 Mount
        try:
            mount_instance = MountManager.new(
                module_id=module.id,
                app_code=application.code,
                name=validated_data["name"],
                environment_name=validated_data["environment_name"],
                mount_path=validated_data["mount_path"],
                source_type=validated_data["source_type"],
                source_name=validated_data.get("source_name"),
                sub_paths=validated_data.get("sub_paths"),
            )
        except IntegrityError:
            raise error_codes.CREATE_VOLUME_MOUNT_FAILED.f(_("同环境和路径挂载卷已存在"))

        if not validated_data.get("source_name"):
            # 创建或更新 Mount source
            configmap_source = validated_data.get("configmap_source") or {}
            controller = init_volume_source_controller(mount_instance.source_type)
            data = configmap_source.get("source_config_data", {})
            controller.create_by_env(
                app_id=mount_instance.module.application.id,
                module_id=mount_instance.module.id,
                env_name=mount_instance.environment_name,
                source_name=mount_instance.get_source_name,
                data=data,
            )

        try:
            slz = MountSLZ(mount_instance)
        except GetSourceConfigDataError as e:
            raise error_codes.CREATE_VOLUME_MOUNT_FAILED.f(_(e))

        # source_config 字段无法被序列化
        data_after = MountSLZ(mount_instance).data
        del data_after["source_config"]
        add_app_audit_record(
            app_code=code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE,
            target=OperationTarget.VOLUME_MOUNT,
            attribute=mount_instance.name,
            module_name=module_name,
            data_after=DataDetail(data=data_after),
        )
        return Response(data=slz.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    @swagger_auto_schema(responses={200: MountSLZ()}, request_body=UpsertMountSLZ)
    def update(self, request, code, module_name, mount_id):
        module = self.get_module_via_path()
        mount_instance = get_object_or_404(Mount, id=mount_id, module_id=module.id)
        data_before = MountSLZ(mount_instance).data
        del data_before["source_config"]

        slz = UpsertMountSLZ(data=request.data, context={"module_id": module.id, "mount_id": mount_instance.id})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data
        controller = init_volume_source_controller(mount_instance.source_type)

        # 更新 Mount
        mount_instance.name = validated_data["name"]
        mount_instance.environment_name = validated_data["environment_name"]
        mount_instance.mount_path = validated_data["mount_path"]
        mount_instance.sub_paths = validated_data["sub_paths"]
        if source_name := validated_data.get("source_name"):
            mount_instance.source_config = controller.build_volume_source(source_name)
        try:
            mount_instance.save(update_fields=["name", "environment_name", "mount_path", "source_config", "sub_paths"])
        except IntegrityError:
            raise error_codes.UPDATE_VOLUME_MOUNT_FAILED.f(_("同环境和路径挂载卷已存在"))

        # 更新 Mount source
        configmap_source = validated_data.get("configmap_source") or {}
        controller.update_by_env(
            app_id=mount_instance.module.application.id,
            module_id=mount_instance.module.id,
            env_name=mount_instance.environment_name,
            source_name=mount_instance.get_source_name,
            data=configmap_source.get("source_config_data"),
        )

        try:
            slz = MountSLZ(mount_instance)
        except GetSourceConfigDataError as e:
            raise error_codes.UPDATE_VOLUME_MOUNT_FAILED.f(_(e))

        data_after = MountSLZ(mount_instance).data
        del data_after["source_config"]
        add_app_audit_record(
            app_code=code,
            tenant_id=module.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.VOLUME_MOUNT,
            attribute=mount_instance.name,
            module_name=module_name,
            data_before=DataDetail(data=data_before),
            data_after=DataDetail(data=data_after),
        )
        return Response(data=slz.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, code, module_name, mount_id):
        module = self.get_module_via_path()
        mount_instance = get_object_or_404(Mount, id=mount_id, module_id=module.id)
        data_before = MountSLZ(mount_instance).data
        del data_before["source_config"]

        controller = init_volume_source_controller(mount_instance.source_type)
        controller.delete_by_env(
            app_id=mount_instance.module.application.id,
            module_id=mount_instance.module.id,
            env_name=mount_instance.environment_name,
            source_name=mount_instance.get_source_name,
        )
        mount_instance.delete()

        add_app_audit_record(
            app_code=code,
            tenant_id=module.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.DELETE,
            target=OperationTarget.VOLUME_MOUNT,
            attribute=mount_instance.name,
            module_name=module_name,
            data_before=DataDetail(data=data_before),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MountSourceViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(query_serializer=QueryMountSourcesSLZ, responses={200: MountSourceSLZ(many=True)})
    def list(self, request, code):
        app = self.get_application()

        slz = QueryMountSourcesSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data

        environment_name = params.get("environment_name")
        source_type = params.get("source_type")

        controller = init_volume_source_controller(source_type)
        queryset = controller.list_by_app(application_id=app.id)

        if environment_name:
            queryset = queryset.filter(environment_name=environment_name)

        slz = MountSourceSLZ(queryset, many=True)
        return Response(data=slz.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=CreateMountSourceSLZ, responses={201: MountSourceSLZ(many=True)})
    def create(self, request, code):
        app = self.get_application()
        enabled = check_persistent_storage_enabled(application=app)
        if not enabled:
            raise error_codes.CREATE_VOLUME_SOURCE_FAILED.f(_("当前应用暂不支持持久存储功能，请联系管理员"))
        slz = CreateMountSourceSLZ(data=request.data, context={"application_id": app.id})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        environment_name = validated_data.get("environment_name")
        source_type = validated_data.get("source_type")
        storage_size = (
            validated_data.get("persistent_storage_source", {}).get("storage_size")
            or settings.DEFAULT_PERSISTENT_STORAGE_SIZE
        )

        params = {"application_id": app.id, "environment_name": environment_name, "storage_size": storage_size}
        if display_name := validated_data.get("display_name"):
            params["display_name"] = display_name

        controller = init_volume_source_controller(source_type)
        source = controller.create_by_app(**params)

        slz = MountSourceSLZ(source)
        return Response(data=slz.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(request_body=UpdateMountSourceSLZ, responses={200: MountSourceSLZ})
    def update(self, request, code):
        app = self.get_application()

        slz = UpdateMountSourceSLZ(data=request.data, context={"application_id": app.id})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        controller = init_volume_source_controller(data.get("source_type"))
        source = controller.model_class.objects.get(application_id=app.id, name=data.get("source_name"))
        source.display_name = data.get("display_name")
        source.save(update_fields=["display_name"])

        slz = MountSourceSLZ(source)
        return Response(data=slz.data, status=status.HTTP_200_OK)

    def destroy(self, request, code):
        app = self.get_application()

        slz = DeleteMountSourcesSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data

        source_type = params.get("source_type")
        source_name = params.get("source_name")

        controller = init_volume_source_controller(source_type)
        controller.delete_by_app(application_id=app.id, source_name=source_name)

        return Response(status=status.HTTP_204_NO_CONTENT)


class StorageClassViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def check(self, request, code):
        """检查应用是否开启相应的 StorageClass"""
        app = self.get_application()
        exists = check_storage_class_exists(
            application=app, storage_class_name=settings.DEFAULT_PERSISTENT_STORAGE_CLASS_NAME
        )
        return Response(exists)
