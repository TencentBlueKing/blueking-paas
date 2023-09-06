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
from dataclasses import asdict
from typing import Dict, Optional

from bkpaas_auth.core.encoder import user_id_encoder
from bkpaas_auth.models import User
from blue_krill.storages.blobstore.exceptions import DownloadFailedError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.cnative.specs.image_parser import ImageParser
from paas_wl.cnative.specs.utils import get_bkapp
from paas_wl.platform.applications.models import Build
from paasng.accessories.iam.helpers import fetch_user_roles
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accessories.smart_advisor.utils import get_failure_hint
from paasng.accounts.permissions.application import application_perm_class
from paasng.dev_resources.sourcectl.exceptions import GitLabBranchNameBugError
from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.dev_resources.sourcectl.version_services import get_version_service
from paasng.engine.constants import RuntimeType
from paasng.engine.deploy.engine_svc import get_all_logs
from paasng.engine.deploy.interruptions import interrupt_deployment
from paasng.engine.deploy.start import DeployTaskRunner, initialize_deployment
from paasng.engine.exceptions import DeployInterruptionFailed
from paasng.engine.models import Deployment
from paasng.engine.models.managers import DeployPhaseManager
from paasng.engine.serializers import (
    CheckPreparationsSLZ,
    CreateDeploymentResponseSLZ,
    CreateDeploymentSLZ,
    DeployFramePhaseSLZ,
    DeploymentResultSLZ,
    DeploymentSLZ,
    DeployPhaseSLZ,
    QueryDeploymentsSLZ,
)
from paasng.engine.workflow import DeploymentCoordinator
from paasng.engine.workflow.protections import ModuleEnvDeployInspector
from paasng.extensions.declarative.exceptions import DescriptionValidationError
from paasng.metrics import DEPLOYMENT_INFO_COUNTER
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.environments.constants import EnvRoleOperation
from paasng.platform.environments.exceptions import RoleNotAllowError
from paasng.platform.environments.utils import env_role_protection_check
from paasng.platform.modules.models import Module
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class DeploymentViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """
    应用部署相关API
    基于engine的build & release
    """

    serializer_class = CreateDeploymentSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            from rest_framework.pagination import LimitOffsetPagination

            self._paginator = LimitOffsetPagination()
            self._paginator.default_limit = 12
        return self._paginator

    @swagger_auto_schema(response_serializer=CheckPreparationsSLZ)
    def check_preparations(self, request, code, module_name, environment):
        """校验用户是否满足部署当前环境的限制条件"""
        env = self.get_env_via_path()
        inspector = ModuleEnvDeployInspector(request.user, env)
        status = inspector.perform()
        return Response(
            data=dict(
                CheckPreparationsSLZ(
                    dict(all_conditions_matched=not status.activated, failed_conditions=status.failed_conditions)
                ).data
            )
        )

    @swagger_auto_schema(request_body=CreateDeploymentSLZ, responses={"201": CreateDeploymentResponseSLZ()})
    def deploy(self, request, code, module_name, environment):
        """部署应用"""
        application = self.get_application()
        module = application.get_module(module_name)
        env = module.get_envs(environment)

        roles = fetch_user_roles(application.code, request.user.username)
        try:
            env_role_protection_check(operation=EnvRoleOperation.DEPLOY.value, env=env, roles=roles)
        except RoleNotAllowError:
            raise error_codes.RESTRICT_ROLE_DEPLOY_ENABLED

        serializer = CreateDeploymentSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.data

        # 选择历史构建的镜像时需要传递 build_id
        build = None
        if build_id := params["advanced_options"].get("build_id"):
            if not Build.objects.filter(pk=build_id, artifact_deleted=False).exists():
                raise error_codes.CANNOT_DEPLOY_APP.f(_("历史版本不存在或已被清理"))
            build = Build.objects.get(pk=build_id)

        manifest = params.get("manifest", None)
        if module.build_config.build_method == RuntimeType.CUSTOM_IMAGE:
            if not manifest:
                version_info = VersionInfo(version_type="tag", version_name=params["version_name"], revision="")
                manifest = self._get_deployable_manifest(application, module, image_tag=params["version_name"])
            else:
                # v1alpha1 的云原生应用无 version_info, 但部署流程强依赖了 version_info 对象, 因此这里构造一个空对象来兼容部署流程
                version_info = VersionInfo("", "", "")
        else:
            version_info = self._get_version_info(request.user, module, params, build=build)

        coordinator = DeploymentCoordinator(env)
        if not coordinator.acquire_lock():
            raise error_codes.CANNOT_DEPLOY_ONGOING_EXISTS

        deployment = None
        try:
            with coordinator.release_on_error():
                deployment = initialize_deployment(
                    env=env,
                    operator=request.user.pk,
                    version_info=version_info,
                    advanced_options=params["advanced_options"],
                    manifest=manifest,
                )
                coordinator.set_deployment(deployment)
                # Start a background deploy task
                DeployTaskRunner(deployment).start()
        except Exception as exception:
            self._handle_deploy_failed(module, deployment, exception)

        assert deployment is not None
        DEPLOYMENT_INFO_COUNTER.labels(
            source_type=module.source_type, environment=environment, status="successful"
        ).inc()
        return JsonResponse(
            data={'deployment_id': deployment.id, 'stream_url': f'/streams/{deployment.id}'},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _get_version_info(user: User, module: Module, params: Dict, build: Optional[Build] = None) -> VersionInfo:
        """Get VersionInfo from user inputted params"""
        if build is not None:
            # 为了让 initialize_deployment 中依赖 VersionInfo 的逻辑能正常运行, 这里根据 build 构造 VersionInfo
            # 但实际上这个 VersionInfo 里的信息并未被使用
            # TODO: 解决这种奇怪的问题, 不管是让 initialize_deployment 不依赖 VersionInfo 或者让这里构造的 VersionInfo 变得有意义
            image_tag = build.image_tag or ""
            return VersionInfo(
                version_type="image",
                version_name=image_tag,
                revision=image_tag,
            )

        version_name = params["version_name"]
        version_type = params["version_type"]
        revision = params.get("revision", None)
        try:
            # 尝试根据 smart_revision 获取最新的 revision
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

        # 如果根据 smart_revision 找不到版本信息时, 就使用前端传递的版本信息 revision
        # 如果前端没有提供 revision 信息, 就报错
        if not revision:
            raise error_codes.CANNOT_GET_REVISION
        return VersionInfo(revision, version_name, version_type)

    @staticmethod
    def _get_deployable_manifest(application, module: Module, image_tag: str) -> Dict:
        """查询 module 关联的 bkapp 模型, 并将其转换成 manifest"""
        bkapp = get_bkapp(application, module)
        try:
            repository = ImageParser(bkapp).get_repository()
        except ValueError as e:
            raise error_codes.CANNOT_DEPLOY_APP.f(str(e))
        # 根据用户输入组装完整镜像名
        assert bkapp.spec.build
        bkapp.spec.build.image = f"{repository}:{image_tag}"
        return bkapp.to_deployable()

    def _handle_deploy_failed(self, module: Module, deployment: Optional[Deployment], exception: Exception):
        DEPLOYMENT_INFO_COUNTER.labels(
            source_type=module.source_type, environment=self.kwargs["environment"], status="failed"
        ).inc()
        if deployment is not None:
            deployment.status = "failed"
            deployment.save(update_fields=["status", "updated"])
        logger.exception("Deploy request exception, please try again later")

        if isinstance(exception, DescriptionValidationError):
            raise ValidationError(_('应用描述文件校验失败：{exception}').format(exception=exception))
        elif isinstance(exception, DownloadFailedError):
            raise error_codes.CANNOT_DEPLOY_APP.f(_("对象存储服务异常, 请稍后再试"))
        raise error_codes.CANNOT_DEPLOY_APP.f(_("部署请求异常，请稍候再试"))

    @swagger_auto_schema(responses={200: DeploymentResultSLZ}, paginator_inspectors=[])
    def get_deployment_result(self, request, code, module_name, uuid):
        """查询部署任务结果"""
        deployment = _get_deployment(self.get_module_via_path(), uuid)
        hint = get_failure_hint(deployment)
        result = {
            'status': deployment.status,
            'logs': get_all_logs(deployment),
            'error_detail': deployment.err_detail,
            'error_tips': asdict(hint),
        }
        return JsonResponse(result)

    @swagger_auto_schema(response_serializer=DeploymentSLZ(many=True), query_serializer=QueryDeploymentsSLZ)
    def list(self, request, code, module_name):
        """
        查询部署历史
        """
        application = self.get_application()
        module = application.get_module(module_name)

        serializer = QueryDeploymentsSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.data

        deployments = Deployment.objects.owned_by_module(module, environment=params.get('environment')).order_by(
            '-created'
        )

        # Filter by operator if provided
        operator = params.get('operator')
        if operator:
            operator = user_id_encoder.encode(settings.USER_TYPE, operator)
            deployments = deployments.filter(operator=operator)

        # Paginator
        page = self.paginator.paginate_queryset(deployments, self.request, view=self)
        serializer = DeploymentSLZ(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    def get_resumable_deployment(self, request, code, module_name, environment):
        app_env = self.get_env_via_path()
        deployment = DeploymentCoordinator(app_env).get_current_deployment()
        if not deployment:
            return Response({})

        serializer = DeploymentSLZ(deployment)
        return Response(serializer.data)

    @swagger_auto_schema(tags=['部署阶段'])
    def user_interrupt(self, request, code, module_name, uuid):
        """由用户手动中断某次部署操作

        当部署处于构建（building）或发布（releasing）状态时，调用该接口会尝试终止当前部署。客户端应该在部署进入
        “构建阶段”后，再允许发送“中断”请求。

        接口说明：

        - 因为部署行为的滞后性，该接口最快需要 1-5 秒钟左右才能成功生效
        - 为了避免用户过于频繁请求中断接口，建议客户端在用户点击中断按钮后，设置 1-3 秒钟的冻结期
        - 当中断成功后，调用接口获取部署结果，会看到 `status` 字段值为 `interrupted`。
        - 该接口并不保证一定能成功中断部署，客户端成功调用该接口，仅代表本次中断请求已被成功接收，具体以最终
          检查到的部署状态码为准。
        """
        deployment = _get_deployment(self.get_module_via_path(), uuid)
        try:
            interrupt_deployment(deployment, request.user)
        except DeployInterruptionFailed as e:
            raise error_codes.DEPLOY_INTERRUPTION_FAILED.f(str(e))
        return Response({})


class DeployPhaseViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    @swagger_auto_schema(tags=['部署阶段'], responses={'200': DeployFramePhaseSLZ(many=True)})
    def get_frame(self, request, code, module_name, environment):
        env = self.get_env_via_path()
        phases = DeployPhaseManager(env).get_or_create_all()
        data = DeployFramePhaseSLZ(phases, many=True).data
        return Response(data=data)

    @swagger_auto_schema(tags=['部署阶段'], responses={'200': DeployPhaseSLZ(many=True)})
    def get_result(self, request, code, module_name, environment, uuid):
        try:
            deployment = Deployment.objects.get(pk=uuid)
        except ObjectDoesNotExist:
            raise error_codes.CANNOT_GET_DEPLOYMENT

        manager = DeployPhaseManager(deployment.app_environment)
        try:
            phases = [deployment.deployphase_set.get(type=type_) for type_ in manager.list_phase_types()]
        except Exception:
            logger.exception("failed to get phase info")
            raise error_codes.CANNOT_GET_DEPLOYMENT_PHASES

        return Response(data=DeployPhaseSLZ(phases, many=True).data)


def _get_deployment(module: Module, uuid: str) -> Deployment:
    """Shortcut for getting deployment object by uuid

    :param module: If the deployment exists, it must belongs to this module, otherwise raise an
        exception
    :raises: APIError when deployment does not exists
    """
    try:
        deployment = Deployment.objects.get(id=uuid)
    except Deployment.DoesNotExist:
        raise error_codes.CANNOT_GET_DEPLOYMENT.f(_("没有 id 为 {id} 的部署记录"), id=uuid)

    if deployment.app_environment.module != module:
        raise error_codes.CANNOT_GET_DEPLOYMENT.f(
            _("模块 {module_name} 下没有 id 为 {id} 的部署记录"), module_name=module.name, id=uuid
        )
    return deployment
