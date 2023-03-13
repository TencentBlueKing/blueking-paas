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
import time

from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from drf_yasg.utils import swagger_auto_schema
from kubernetes.dynamic.exceptions import UnprocessibleEntityError
from pydantic import ValidationError as PDValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.cnative.specs.addresses import get_exposed_url
from paas_wl.cnative.specs.constants import BKPAAS_DEPLOY_ID_ANNO_KEY, DeployStatus
from paas_wl.cnative.specs.credentials import get_references, validate_references
from paas_wl.cnative.specs.events import list_events
from paas_wl.cnative.specs.models import AppModelDeploy, AppModelResource, to_error_string, update_app_resource
from paas_wl.cnative.specs.procs.differ import get_online_replicas_diff
from paas_wl.cnative.specs.resource import deploy, get_mres_from_cluster
from paas_wl.cnative.specs.serializers import (
    AppModelResourceSerializer,
    CreateDeploySerializer,
    DeployDetailSerializer,
    DeployPrepResultSLZ,
    DeploySerializer,
    MresStatusSLZ,
    QueryDeploysSerializer,
)
from paas_wl.cnative.specs.tasks import AppModelDeployStatusPoller, DeployStatusHandler
from paas_wl.cnative.specs.v1alpha1.bk_app import BkAppResource
from paas_wl.utils.error_codes import error_codes
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.views import ApplicationCodeInPathMixin

logger = logging.getLogger(__name__)


class MresViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """管理应用模型资源"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={200: AppModelResourceSerializer})
    def retrieve(self, request, code):
        """查看应用模型资源的当前值"""
        application = self.get_application()
        model_resource = get_object_or_404(AppModelResource, application_id=application.id)
        return Response(AppModelResourceSerializer(model_resource).data)

    @swagger_auto_schema(responses={200: AppModelResourceSerializer})
    def update(self, request, code):
        """完整更新应用模型资源，需提供所有字段"""
        application = self.get_application()
        update_app_resource(application, request.data)
        model_resource = AppModelResource.objects.get(application_id=application.id)
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

        manifest = serializer.validated_data.get("manifest")
        try:
            credential_refs = get_references(manifest)
            validate_references(application, credential_refs)
        except ValueError:
            raise error_codes.DEPLOY_BKAPP_FAILED.f("invalid image-credentials")

        # TODO: 检查 manifest 是否有变化
        if manifest:
            update_app_resource(application, manifest)

        # Get current module resource object
        model_resource = AppModelResource.objects.get(application_id=application.id)
        # TODO: Allow use other revisions
        revision = model_resource.revision
        # TODO: read name from request data or generate by model resource payload
        # Add current timestamp in name to avoid conflicts
        default_name = f'{application.code}-{revision.pk}-{int(time.time())}'

        # TODO: Integrity Check
        deployment = AppModelDeploy.objects.create(
            application_id=application.id,
            module_id=module.id,
            environment_name=env.environment,
            name=default_name,
            revision=revision,
            status=DeployStatus.PENDING.value,
            operator=request.user,
        )

        try:
            manifest = deploy(env, deployment.build_manifest(env, credential_refs=credential_refs))
        except UnprocessibleEntityError as e:
            # 格式错误类异常（422）允许将错误信息提供给用户
            raise error_codes.DEPLOY_BKAPP_FAILED.f(
                f"app: {application.code}, env: {environment}, summary: {e.summary()}"
            )
        except Exception as e:
            logger.exception(
                "failed to deploy bkapp, app: %s, code: %s, env: %s, reason: %s",
                application.name,
                application.code,
                environment,
                e,
            )
            raise error_codes.DEPLOY_BKAPP_FAILED.f(f"app: {application.code}, env: {environment}")

        # Poll status in background
        AppModelDeployStatusPoller.start({'deploy_id': deployment.id}, DeployStatusHandler)
        return Response(manifest)

    @swagger_auto_schema(request_body=CreateDeploySerializer, responses={"200": DeployPrepResultSLZ()})
    def prepare(self, request, code, module_name, environment):
        """每次部署前调用，接收的参数与部署一致，返回需用户关注的二次确认信息，比如
        某些进程的副本数将被重写，等等。

        - 客户端：当 `proc_replicas_changes` 没有数据时，不展示额外信息，只显示普通的
          二次确认框
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


class MresStatusViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """应用模型资源状态相关视图"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

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

        return Response(
            MresStatusSLZ(
                {
                    "deployment": latest_dp,
                    "ingress": {"url": get_exposed_url(env)},
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
