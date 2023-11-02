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

from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from kubernetes.dynamic.exceptions import ResourceNotFoundError, UnprocessibleEntityError
from pydantic import ValidationError as PDValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.cnative.specs.constants import BKPAAS_DEPLOY_ID_ANNO_KEY, MountEnvName, ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.credentials import get_references, validate_references
from paas_wl.bk_app.cnative.specs.events import list_events
from paas_wl.bk_app.cnative.specs.exceptions import GetSourceConfigDataError, InvalidImageCredentials
from paas_wl.bk_app.cnative.specs.image_parser import ImageParser
from paas_wl.bk_app.cnative.specs.models import (
    AppModelDeploy,
    AppModelResource,
    AppModelRevision,
    Mount,
    to_error_string,
    update_app_resource,
)
from paas_wl.bk_app.cnative.specs.mounts import VolumeSourceManager
from paas_wl.bk_app.cnative.specs.procs.differ import get_online_replicas_diff
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP, PLAN_TO_REQUEST_QUOTA_MAP
from paas_wl.bk_app.cnative.specs.resource import get_mres_from_cluster
from paas_wl.bk_app.cnative.specs.serializers import (
    AppModelResourceSerializer,
    AppModelRevisionSerializer,
    CreateDeploySerializer,
    DeployDetailSerializer,
    DeployPrepResultSLZ,
    DeploySerializer,
    MountSLZ,
    MresStatusSLZ,
    QueryDeploysSerializer,
    QueryMountsSLZ,
    ResQuotaPlanSLZ,
    UpsertMountSLZ,
)
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.images.models import AppImageCredential, AppUserCredential
from paasng.accessories.publish.entrance.exposer import get_exposed_url
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.engine.deploy.release.operator import release_by_k8s_operator
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


class MresViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """管理应用模型资源"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={200: AppModelResourceSerializer})
    def retrieve(self, request, code, module_name):
        """查看应用模型资源的当前值"""
        application = self.get_application()
        module = self.get_module_via_path()
        model_resource = get_object_or_404(AppModelResource, application_id=application.id, module_id=module.id)
        return Response(AppModelResourceSerializer(model_resource).data)

    @swagger_auto_schema(responses={200: AppModelResourceSerializer})
    def update(self, request, code, module_name):
        """完整更新应用模型资源，需提供所有字段"""
        application = self.get_application()
        module = self.get_module_via_path()
        update_app_resource(application, module, request.data)
        model_resource = AppModelResource.objects.get(application_id=application.id, module_id=module.id)
        return Response(AppModelResourceSerializer(model_resource).data)


class MresDeploymentsViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """应用模型资源部署相关视图"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @cached_property
    def paginator(self):
        """Return a pagination object with a small default limit"""
        _paginator = LimitOffsetPagination()
        _paginator.default_limit = 20
        return _paginator

    @swagger_auto_schema(responses={"200": DeploySerializer})
    def retrieve(self, request, code, module_name, environment, deploy_id):
        """获取某个部署对象的详细信息"""
        try:
            deployment = AppModelDeploy.objects.get(pk=deploy_id)
        except AppModelDeploy.DoesNotExist:
            raise error_codes.GET_DEPLOYMENT_FAILED.f(f"id=`{deploy_id}` not found.")
        return Response(DeployDetailSerializer(deployment).data)

    # 该接口已注册到 APIGW
    # 网关名称 get_cnative_deployments_list
    # 请勿随意修改该接口协议
    @swagger_auto_schema(responses={"200": DeploySerializer(many=True)}, query_serializer=QueryDeploysSerializer)
    def list(self, request, code, module_name, environment):
        """查询历史部署对象"""
        qs = self.get_queryset().order_by('-created')

        # Filter QuerySet
        serializer = QueryDeploysSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        if operator := serializer.validated_data.get('operator'):
            qs = qs.filter(operator=user_id_encoder.encode(settings.USER_TYPE, operator))

        page = self.paginator.paginate_queryset(qs, self.request, view=self)
        return self.paginator.get_paginated_response(data=DeploySerializer(page, many=True).data)

    # 该接口已注册到 APIGW
    # 网关名称 deploy_cnative_app
    # 请勿随意修改该接口协议
    @swagger_auto_schema(request_body=CreateDeploySerializer)
    def create(self, request, code, module_name, environment):
        """创建一次新的部署

        TODO 这里目前先包含配置更新的逻辑（manifest + update_app_resource），预期应该是保存与部署分离
        """
        application = self.get_application()
        module = self.get_module_via_path()
        env = self.get_env_via_path()

        serializer = CreateDeploySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update the current manifest when "manifest" field was provided, the data
        # will be validated in `update_app_resource` function.
        # TODO: 当 manifest 提供时，检查 manifest 是否有变化
        if manifest := serializer.validated_data.get("manifest"):
            update_app_resource(application, module, manifest)

        # Get current module resource object
        model_resource = AppModelResource.objects.get(application_id=application.id, module_id=module.id)
        # TODO: Allow use other revisions
        revision = model_resource.revision

        # Try to get and validate the image credentials, will raise InvalidImageCredentials when any refs are invalid
        try:
            credential_refs = get_references(revision.json_value)
            validate_references(application, credential_refs)
        except InvalidImageCredentials:
            raise error_codes.DEPLOY_BKAPP_FAILED.f("invalid image-credentials")
        # flush credentials if needed
        if credential_refs:
            AppImageCredential.objects.flush_from_refs(
                application=application, wl_app=env.wl_app, references=credential_refs
            )

        try:
            release_by_k8s_operator(env, revision, operator=request.user.pk)
        except UnprocessibleEntityError as e:
            # 格式错误类异常（422），允许将错误信息提供给用户
            raise error_codes.DEPLOY_BKAPP_FAILED.f(
                f"{code}, module: {module_name}, env: {environment}, summary: {e.summary()}"
            )
        except ResourceNotFoundError:
            # 集群内没有 BkApp 等 PaaS Operator 资源，可以暴露给用户
            raise error_codes.DEPLOY_BKAPP_FAILED.f(
                f"{code}, module: {module_name}, env: {environment}, reason: bkpaas-app-operator not ready"
            )
        except Exception as e:
            logger.exception(
                "failed to deploy bkapp, code: %s, module: %s, env: %s, reason: %s", code, module_name, environment, e
            )
            raise error_codes.DEPLOY_BKAPP_FAILED.f(f"{code}, module: {module_name}, env: {environment}")
        revision.refresh_from_db()
        return Response(revision.deployed_value)

    @swagger_auto_schema(request_body=CreateDeploySerializer, responses={"200": DeployPrepResultSLZ()})
    def prepare(self, request, code, module_name, environment):
        """每次部署前调用，接收的参数与部署一致，返回需用户关注的二次确认信息，比如某些进程的副本数将被重写，等等。

        - 客户端：当 `proc_replicas_changes` 没有数据时，不展示额外信息，只显示普通的二次确认框
        """
        env = self.get_env_via_path()
        slz = CreateDeploySerializer(data=request.data)
        slz.is_valid(raise_exception=True)

        # validate incoming manifest
        try:
            new_res = BkAppResource(**slz.validated_data.get("manifest"))
        except PDValidationError as e:
            raise ValidationError(to_error_string(e))

        changes = get_online_replicas_diff(env, new_res)
        return Response(DeployPrepResultSLZ({'proc_replicas_changes': changes}).data)

    def get_queryset(self) -> models.QuerySet:
        """Get the AppModelDeploy QuerySet object"""
        application = self.get_application()
        module = self.get_module_via_path()
        return AppModelDeploy.objects.filter(
            application_id=application.id, module_id=module.id, environment_name=self.kwargs["environment"]
        )


class MresVersionViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """应用资源版本相关视图"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={"200": AppModelRevisionSerializer})
    def retrieve(self, request, code, module_name, environment, revision_id):
        """获取某个部署版本的详细信息"""
        try:
            revision = AppModelRevision.objects.get(pk=revision_id)
        except AppModelRevision.DoesNotExist:
            raise error_codes.GET_DEPLOYMENT_FAILED.f(f"app model revision id {revision_id} not found")
        return Response(AppModelRevisionSerializer(revision).data)


class MresStatusViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """应用模型资源状态相关视图"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    # 该接口已注册到 APIGW
    # 网关名称 get_cnative_app_status
    # 请勿随意修改该接口协议
    @swagger_auto_schema(responses={"200": MresStatusSLZ})
    def retrieve(self, request, code, module_name, environment):
        """查看应用模型资源当前状态"""
        env = self.get_env_via_path()
        try:
            latest_dp: AppModelDeploy = AppModelDeploy.objects.filter_by_env(env).latest("created")
        except AppModelDeploy.DoesNotExist:
            raise error_codes.GET_DEPLOYMENT_FAILED.f("App not deployed")

        # Read model resource from cluster
        mres = get_mres_from_cluster(env)
        if not mres:
            raise error_codes.GET_MRES_FAILED.f(f"App: {code}, env: {environment}")
        self.check_applied_deployment(mres, latest_dp)
        url_obj = get_exposed_url(env)

        return Response(
            MresStatusSLZ(
                {
                    "deployment": latest_dp,
                    "ingress": {"url": url_obj.address if url_obj else None},
                    "conditions": mres.status.conditions,
                    "events": list_events(env, latest_dp.created),
                }
            ).data
        )

    @staticmethod
    def check_applied_deployment(mres: BkAppResource, deployment: AppModelDeploy):
        """Check if a BkAppResource has applied given deployment

        :raise: APIError when check failed
        """
        deploy_id = mres.metadata.annotations.get(BKPAAS_DEPLOY_ID_ANNO_KEY)
        if deploy_id is None:
            raise error_codes.INVALID_MRES.f(f"missing Annotations[{BKPAAS_DEPLOY_ID_ANNO_KEY!r}]")
        if str(deploy_id) != str(deployment.id):
            raise error_codes.GET_DEPLOYMENT_FAILED.f("The deployed version is inconsistent with the cluster state")


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
            repository = cfg.image_repository
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
        environment_name = params.get('environment_name')
        if environment_name:
            mounts = mounts.filter(environment_name=environment_name)
        # Filter by source_type if provided
        source_type = params.get('source_type')
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
        slz = UpsertMountSLZ(data=request.data, context={'module_id': module.id})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        # 创建 Mount
        try:
            mount_instance = Mount.objects.new(
                module_id=module.id,
                app_code=application.code,
                name=validated_data['name'],
                environment_name=validated_data['environment_name'],
                mount_path=validated_data['mount_path'],
                source_type=validated_data['source_type'],
                region=application.region,
            )
        except IntegrityError:
            raise error_codes.CREATE_VOLUME_MOUNT_FAILED.f(_("同环境和路径挂载卷已存在"))

        # 创建或更新 Mount source
        Mount.objects.upsert_source(mount_instance, validated_data['source_config_data'])

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

        slz = UpsertMountSLZ(data=request.data, context={'module_id': module.id, 'mount_id': mount_instance.id})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        # 更新 Mount
        mount_instance.name = validated_data['name']
        mount_instance.environment_name = validated_data['environment_name']
        mount_instance.mount_path = validated_data['mount_path']
        try:
            mount_instance.save(update_fields=['name', 'environment_name', 'mount_path'])
        except IntegrityError:
            raise error_codes.UPDATE_VOLUME_MOUNT_FAILED.f(_("同环境和路径挂载卷已存在"))

        # 创建或更新 Mount source
        Mount.objects.upsert_source(mount_instance, validated_data['source_config_data'])

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
