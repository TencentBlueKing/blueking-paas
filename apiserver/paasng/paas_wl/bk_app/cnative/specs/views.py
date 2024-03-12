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
from contextlib import suppress
from urllib.parse import quote

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from moby_distribution.registry.utils import parse_image
from rest_framework import status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.cnative.specs.constants import MountEnvName, ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.exceptions import GetSourceConfigDataError
from paas_wl.bk_app.cnative.specs.image_parser import ImageParser
from paas_wl.bk_app.cnative.specs.models import (
    AppModelResource,
    AppModelRevision,
    Mount,
)
from paas_wl.bk_app.cnative.specs.mounts import VolumeSourceManager
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP, PLAN_TO_REQUEST_QUOTA_MAP
from paas_wl.bk_app.cnative.specs.serializers import (
    AppModelRevisionSerializer,
    MountSLZ,
    QueryMountsSLZ,
    ResQuotaPlanSLZ,
    UpsertMountSLZ,
)
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.images.models import AppUserCredential
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
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
    def _validate_registry_permission(self, registry_service: DockerRegistryController):
        """Validates the registry permission by attempting to touch it.

        :raise: error_codes.INVALID_CREDENTIALS: If the credentials are invalid or the repository is unreachable.
        """
        with suppress(Exception):
            # bkrepo 的 docker 仓库，镜像凭证没有填写正确时，.touch() 时会抛出异常
            if registry_service.touch():
                return
            raise error_codes.INVALID_CREDENTIALS.f(_("权限不足或仓库不可达"))

    @swagger_auto_schema(response_serializer=AlternativeVersionSLZ(many=True))
    def list_tags(self, request, code, module_name):
        """列举 bkapp 声明的镜像仓库中的所有 tag, 仅支持 v1alpha2 版本的云原生应用"""
        application = self.get_application()
        module = self.get_module_via_path()

        cfg = BuildConfig.objects.get_or_create_by_module(module)
        if cfg.image_repository:
            # 如果用户填的是 dockerhub 的镜像仓库，则补齐 registry 的域名信息
            parsed = parse_image(cfg.image_repository, default_registry="index.docker.io")
            repository = f"{parsed.domain}/{parsed.name}"
            credential_name = cfg.image_credential_name
        else:
            # TODO: 数据迁移后删除以下代码
            model_resource = get_object_or_404(AppModelResource, application_id=application.id, module_id=module.id)
            bkapp = BkAppResource(**model_resource.revision.json_value)

            try:
                repository = ImageParser(bkapp).get_repository()
            except ValueError as e:
                raise error_codes.INVALID_MRES.f(str(e))

            assert bkapp.spec.build
            if repository != bkapp.spec.build.image:
                logger.warning("BkApp 的 spec.build.image 为镜像全名, 将忽略 tag 部分")

            credential_name = bkapp.spec.build.imageCredentialsName

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
            raise error_codes.LIST_TAGS_FAILED.f(_("%s的仓库信息查询异常") % code)
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
            mount_instance = Mount.objects.new(
                module_id=module.id,
                app_code=application.code,
                name=validated_data["name"],
                environment_name=validated_data["environment_name"],
                mount_path=validated_data["mount_path"],
                source_type=validated_data["source_type"],
                region=application.region,
            )
        except IntegrityError:
            raise error_codes.CREATE_VOLUME_MOUNT_FAILED.f(_("同环境和路径挂载卷已存在"))

        # 创建或更新 Mount source
        Mount.objects.upsert_source(mount_instance, validated_data["source_config_data"])

        try:
            slz = MountSLZ(mount_instance)
        except GetSourceConfigDataError as e:
            raise error_codes.CREATE_VOLUME_MOUNT_FAILED.f(_(e))
        return Response(data=slz.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    @swagger_auto_schema(responses={200: MountSLZ()}, request_body=UpsertMountSLZ)
    def update(self, request, code, module_name, mount_id):
        module = self.get_module_via_path()
        mount_instance = get_object_or_404(Mount, id=mount_id, module_id=module.id)

        slz = UpsertMountSLZ(data=request.data, context={"module_id": module.id, "mount_id": mount_instance.id})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        # 更新 Mount
        mount_instance.name = validated_data["name"]
        mount_instance.environment_name = validated_data["environment_name"]
        mount_instance.mount_path = validated_data["mount_path"]
        try:
            mount_instance.save(update_fields=["name", "environment_name", "mount_path"])
        except IntegrityError:
            raise error_codes.UPDATE_VOLUME_MOUNT_FAILED.f(_("同环境和路径挂载卷已存在"))

        # 创建或更新 Mount source
        Mount.objects.upsert_source(mount_instance, validated_data["source_config_data"])

        # 需要删除对应的 k8s volume 资源
        if mount_instance.environment_name in (MountEnvName.PROD.value, MountEnvName.STAG.value):
            opposite_env_map = {
                MountEnvName.STAG.value: MountEnvName.PROD.value,
                MountEnvName.PROD.value: MountEnvName.STAG.value,
            }
            env = module.get_envs(environment=opposite_env_map.get(mount_instance.environment_name))
            VolumeSourceManager(env).delete_source_config(mount_instance)

        try:
            slz = MountSLZ(mount_instance)
        except GetSourceConfigDataError as e:
            raise error_codes.UPDATE_VOLUME_MOUNT_FAILED.f(_(e))
        return Response(data=slz.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, code, module_name, mount_id):
        module = self.get_module_via_path()
        mount_instance = get_object_or_404(Mount, id=mount_id, module_id=module.id)

        # 需要删除对应的 k8s volume 资源
        for env in module.get_envs():
            VolumeSourceManager(env).delete_source_config(mount_instance)

        mount_instance.source.delete()
        mount_instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
