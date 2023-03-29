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
import datetime
import logging
from dataclasses import asdict
from typing import Dict, Optional

from bkpaas_auth.models import User, user_id_encoder
from blue_krill.storages.blobstore.exceptions import DownloadFailedError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.cluster.shim import EnvClusterService
from paas_wl.monitoring.metrics.exceptions import (
    AppInstancesNotFoundError,
    AppMetricNotSupportedError,
    RequestMetricBackendError,
)
from paas_wl.monitoring.metrics.shim import list_app_proc_all_metrics, list_app_proc_metrics
from paas_wl.monitoring.metrics.utils import MetricSmartTimeRange
from paas_wl.platform.system_api.serializers import InstanceMetricsResultSerializer, ResourceMetricsResultSerializer
from paas_wl.release_controller.api import get_latest_build_id
from paasng.accessories.iam.helpers import fetch_user_roles
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accessories.smart_advisor.utils import get_failure_hint
from paasng.accounts.permissions.application import application_perm_class
from paasng.dev_resources.sourcectl.exceptions import GitLabBranchNameBugError
from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.dev_resources.sourcectl.version_services import get_version_service
from paasng.engine.configurations.config_var import (
    generate_env_vars_by_region_and_env,
    generate_env_vars_for_bk_platform,
)
from paasng.engine.constants import AppInfoBuiltinEnv, AppRunTimeBuiltinEnv, NoPrefixAppRunTimeBuiltinEnv
from paasng.engine.deploy.archive import OfflineManager
from paasng.engine.deploy.engine_svc import get_all_logs
from paasng.engine.deploy.release import create_release
from paasng.engine.deploy.start import DeployTaskRunner, initialize_deployment
from paasng.engine.exceptions import DeployInterruptionFailed, OfflineOperationExistError
from paasng.engine.models.config_var import ENVIRONMENT_NAME_FOR_GLOBAL, ConfigVar, add_prefix_to_key
from paasng.engine.models.deployment import Deployment, interrupt_deployment
from paasng.engine.models.managers import ConfigVarManager, DeployPhaseManager, ExportedConfigVars, PlainConfigVar
from paasng.engine.models.offline import OfflineOperation
from paasng.engine.models.operations import ModuleEnvironmentOperations
from paasng.engine.models.processes import ProcessManager
from paasng.engine.serializers import (
    CheckPreparationsSLZ,
    ConfigVarApplyResultSLZ,
    ConfigVarImportSLZ,
    ConfigVarSLZ,
    CreateDeploymentResponseSLZ,
    CreateDeploymentSLZ,
    CreateOfflineOperationSLZ,
    CustomDomainsConfigSLZ,
    DeployFramePhaseSLZ,
    DeploymentResultSLZ,
    DeploymentSLZ,
    DeployPhaseSLZ,
    GetReleasedInfoSLZ,
    ListConfigVarsSLZ,
    OfflineOperationSLZ,
    OperationSLZ,
    QueryDeploymentsSLZ,
    QueryOperationsSLZ,
    ResourceMetricsSLZ,
)
from paasng.engine.workflow import DeploymentCoordinator
from paasng.engine.workflow.protections import ModuleEnvDeployInspector
from paasng.extensions.declarative.exceptions import DescriptionValidationError
from paasng.metrics import DEPLOYMENT_INFO_COUNTER
from paasng.platform.applications.constants import AppEnvironment, AppFeatureFlag
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.environments.constants import EnvRoleOperation
from paasng.platform.environments.exceptions import RoleNotAllowError
from paasng.platform.environments.utils import env_role_protection_check
from paasng.platform.modules.models import Module
from paasng.publish.entrance.exposer import env_is_deployed, get_exposed_url
from paasng.publish.entrance.preallocated import get_preallocated_url
from paasng.utils.error_codes import error_codes
from paasng.utils.views import allow_resp_patch

logger = logging.getLogger(__name__)


class ReleasedInfoViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    serializer_class = GetReleasedInfoSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(deprecated=True)
    def get_current_info(self, request, code, module_name, environment):
        module_env = self.get_env_via_path()
        serializer = self.serializer_class(request.query_params)

        try:
            deployment = Deployment.objects.filter_by_env(env=module_env).latest_succeeded()
        except Deployment.DoesNotExist:
            raise error_codes.APP_NOT_RELEASED

        data = {
            'deployment': DeploymentSLZ(deployment).data,
            'exposed_link': {"url": deployment.app_environment.get_exposed_link()},
        }
        if serializer.data['with_processes']:
            _specs = ProcessManager(module_env.engine_app).list_processes_specs()
            # Change structure of "specs", make it compatible with frontend client
            specs = [{spec['name']: spec} for spec in _specs]
            data['processes'] = specs
        return Response(data)

    @allow_resp_patch
    def get_current_state(self, request, code, module_name, environment):
        """
        - /api/bkapps/applications/{code}/envs/{environment}/deployments/latest/
        - path param: code, app名, 必须
        - path param: environment, 部署环境(stag或者prod), 必须
        - get param: with_processes, 是否返回进程信息，传递 true 时返回，默认不返回
        """
        app = self.get_application()
        module_env = self.get_env_via_path()
        serializer = self.serializer_class(request.query_params)

        deployment_data = None
        offline_data = None
        default_access_entrance = get_preallocated_url(module_env)

        if module_env.is_offlined:
            try:
                offline_operation = OfflineOperation.objects.filter(app_environment=module_env).latest_succeeded()
            except OfflineOperation.DoesNotExist:
                raise error_codes.APP_NOT_RELEASED
            offline_data = OfflineOperationSLZ(offline_operation).data

        # Check if current env is running
        if env_is_deployed(module_env):
            deployment_data = self.get_deployment_data(module_env)

        if not any([deployment_data, offline_data]):
            raise error_codes.APP_NOT_RELEASED

        exposed_link = get_exposed_url(module_env)
        data = {
            "is_offlined": module_env.is_offlined,
            'deployment': deployment_data,
            "offline": offline_data,
            'exposed_link': {"url": exposed_link.address if exposed_link else None},
            "default_access_entrance": {"url": default_access_entrance.address if default_access_entrance else None},
            "feature_flag": {  # 应用 feature flag 接口已独立提供，后续 feature flag 不再往这里同步
                "release_to_bk_market": app.feature_flag.has_feature(AppFeatureFlag.RELEASE_TO_BLUEKING_MARKET),
                "release_to_wx_miniprogram": app.feature_flag.has_feature(
                    AppFeatureFlag.RELEASE_TO_WEIXIN_MINIPROGRAM
                ),
            },
        }
        if serializer.data['with_processes']:
            _specs = ProcessManager(module_env.engine_app).list_processes_specs()
            # Change structure of "specs", make it compatible with frontend client
            specs = [{spec['name']: spec} for spec in _specs]
            data['processes'] = specs

        return Response(data)

    @staticmethod
    def get_deployment_data(env) -> Optional[Dict]:
        """Try to get the latest deployment data by querying Deployment model"""
        try:
            deployment = Deployment.objects.filter_by_env(env=env).latest_succeeded()
        except Deployment.DoesNotExist:
            # Cloud-native app does not has any deployment objects
            return None
        return DeploymentSLZ(deployment).data


class ReleasesViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def release(self, request, code, module_name, environment):
        """
        单纯的release
        - /api/bkapps/applications/{code}/envs/{environment}/release/
        - param: env, 选择发布环境
        ----
        """
        application = self.get_application()
        module = application.get_module(module_name)

        if environment == ENVIRONMENT_NAME_FOR_GLOBAL:
            application_envs = module.envs.all()
        else:
            application_envs = module.envs.filter(environment=environment)

        for application_env in application_envs:
            try:
                build_id = get_latest_build_id(application_env)
                if build_id:
                    create_release(application_env, str(build_id))
            except Exception:
                raise error_codes.CANNOT_DEPLOY_APP.f(_(u"服务异常"))

        return Response(status=status.HTTP_201_CREATED)


class ConfigVarImportExportViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @staticmethod
    def make_exported_vars_response(data: ExportedConfigVars, file_name: str) -> HttpResponse:
        """Generate http response(with attachment) for given config vars data

        :param data: config vars data
        :param file_name: attachment filename
        """
        response = HttpResponse(data.to_file_content(), content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response

    def get_queryset(self):
        return ConfigVar.objects.filter(module=self.get_module_via_path(), is_builtin=False)

    @swagger_auto_schema(
        request_body=ConfigVarImportSLZ,
        tags=['环境配置'],
        responses={201: ConfigVarApplyResultSLZ()},
    )
    def import_by_file(self, request, **kwargs):
        """从文件导入环境变量"""
        module = self.get_module_via_path()
        # Check file format
        try:
            slz = ConfigVarImportSLZ(data=request.FILES, context={"module": module})
            slz.is_valid(raise_exception=True)
        except ValidationError as e:
            raise getattr(error_codes, e.get_codes()["error"], e)

        # Import config vars
        env_variables = slz.validated_data["env_variables"]

        apply_result = ConfigVarManager().apply_vars_to_module(module, env_variables)
        res = ConfigVarApplyResultSLZ(apply_result)
        return Response(res.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=['环境配置'])
    def export_to_file(self, request, code, module_name):
        """导出环境变量到文件"""
        list_vars_slz = ListConfigVarsSLZ(data=request.query_params)
        list_vars_slz.is_valid(raise_exception=True)
        order_by = list_vars_slz.data['order_by']

        queryset = (
            self.get_queryset().filter(is_builtin=False).select_related('environment').order_by(order_by, 'is_global')
        )

        result = ExportedConfigVars.from_list(list(queryset))
        return self.make_exported_vars_response(result, f"bk_paas3_{code}_{module_name}_config_vars.yaml")

    @swagger_auto_schema(tags=['环境配置'])
    def template(self, request, **kwargs):
        """返回yaml模板"""
        config_vars = ExportedConfigVars(
            env_variables=[
                PlainConfigVar(key="PROD", value="example", environment_name="prod", description="example"),
                PlainConfigVar(key="STAG", value="example", environment_name="stag", description="example"),
                PlainConfigVar(key="GLOBAL", value="example", environment_name="_global_", description="example"),
            ]
        )
        return self.make_exported_vars_response(config_vars, 'bk_paas3_config_vars_template.yaml')


@method_decorator(name="update", decorator=swagger_auto_schema(request_body=ConfigVarSLZ, tags=['环境配置']))
@method_decorator(name="create", decorator=swagger_auto_schema(request_body=ConfigVarSLZ, tags=['环境配置']))
@method_decorator(name="list", decorator=swagger_auto_schema(query_serializer=ListConfigVarsSLZ, tags=['环境配置']))
@method_decorator(name="destroy", decorator=swagger_auto_schema(tags=['环境配置']))
class ConfigVarViewSet(viewsets.ModelViewSet, ApplicationCodeInPathMixin):
    """ViewSet for config vars"""

    pagination_class = None
    serializer_class = ConfigVarSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def get_object(self):
        """Get current ConfigVar object by path var"""
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['id'])

    def get_queryset(self):
        return ConfigVar.objects.filter(module=self.get_module_via_path(), is_builtin=False)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["module"] = self.get_module_via_path()
        return context

    @swagger_auto_schema(
        tags=['环境配置'],
        responses={201: ConfigVarApplyResultSLZ()},
    )
    def clone(self, request, **kwargs):
        """从某一模块克隆环境变量至当前模块"""
        application = self.get_application()
        source = application.get_module(module_name=self.kwargs['source_module_name'])
        dest = self.get_module_via_path()

        res_nums = ConfigVarManager().clone_vars(source, dest)

        slz = ConfigVarApplyResultSLZ(res_nums)
        return Response(slz.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(query_serializer=ListConfigVarsSLZ, tags=['环境配置'], responses={200: ConfigVarSLZ(many=True)})
    def list(self, request, **kwargs):
        """查看应用的所有环境变量"""
        input_slz = ListConfigVarsSLZ(data=request.query_params)
        input_slz.is_valid(raise_exception=True)

        config_vars = self.get_queryset().select_related('environment')

        # Filter by environment name
        environment_name = input_slz.data.get('environment_name')
        if environment_name:
            config_vars = config_vars.filter_by_environment_name(environment_name)

        # Change result ordering
        config_vars = config_vars.order_by(input_slz.data['order_by'], 'is_global')

        serializer = self.serializer_class(config_vars, many=True)
        return Response(serializer.data)


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
        version_info = self._get_version_info(request.user, module, params)

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
    def _get_version_info(user: User, module: Module, params: Dict) -> VersionInfo:
        """Get VersionInfo from user inputted params"""
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


class OfflineViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """
    应用下线相关API
    基于stop process实现
    """

    serializer_class = CreateOfflineOperationSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def offline(self, request, code, module_name, environment):
        """
        发起下线请求
        - /api/bkapps/applications/{code}/envs/{environment}/offlines/
        """
        application = self.get_application()
        module = application.get_module(module_name)

        serializer = CreateOfflineOperationSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        app_environment = module.get_envs(environment)
        manager = OfflineManager(env=app_environment)

        roles = fetch_user_roles(application.code, request.user.username)
        try:
            # 现在部署和下架使用相同的操作识别
            env_role_protection_check(operation=EnvRoleOperation.DEPLOY.value, env=app_environment, roles=roles)
        except RoleNotAllowError:
            raise error_codes.RESTRICT_ROLE_DEPLOY_ENABLED

        try:
            offline_operation = manager.perform_env_offline(operator=request.user.pk)
        except Deployment.DoesNotExist:
            # 未曾部署，跳过该环境的下架操作
            raise error_codes.CANNOT_OFFLINE_APP.f(_("没有找到对应的部署记录，不允许下架"))
        except OfflineOperationExistError:
            # 在规定时间内，存在下架操作
            raise error_codes.CANNOT_OFFLINE_APP.f(_("存在正在进行的下架任务，请勿重复操作"))
        except Exception as e:
            logger.exception("app offline error")
            raise error_codes.CANNOT_OFFLINE_APP.f(str(e))
        else:
            result = {
                'offline_operation_id': offline_operation.id,
            }
            return JsonResponse(data=result, status=status.HTTP_201_CREATED)

    def get_offline_result(self, request, code, module_name, uuid):
        """
        查询下线任务结果
        - /api/bkapps/applications/{code})/offline_operations/{uuid}/result/
        - path param: code, app名
        - path param: uuid, 部署任务的uuid(即deployment_id)
        """
        application = self.get_application()
        module = application.get_module(module_name)

        try:
            offline_operation = OfflineOperation.objects.get(id=uuid, app_environment__module=module)
        except OfflineOperation.DoesNotExist:
            raise error_codes.CANNOT_GET_OFFLINE.f(_(f"{code} 没有id为 {uuid} 的下架记录"))
        else:
            data = OfflineOperationSLZ(instance=offline_operation).data
            return JsonResponse(data)

    @swagger_auto_schema(response_serializer=OfflineOperationSLZ)
    def get_resumable_offline_operations(self, request, code, module_name, environment):
        """查询可恢复的下架操作"""
        application = self.get_application()
        module = application.get_module(module_name)

        app_env = module.envs.get(environment=environment)
        try:
            offline_operation = OfflineOperation.objects.filter(app_environment=app_env).get_latest_resumable(
                max_resumable_seconds=settings.ENGINE_OFFLINE_RESUMABLE_SECS
            )
        except OfflineOperation.DoesNotExist:
            return Response({})

        serializer = OfflineOperationSLZ(instance=offline_operation)
        return Response({"result": serializer.data})


class OperationsViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """
    应用操作记录相关API
    比如：部署记录和下线记录
    """

    serializer_class = QueryOperationsSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            from rest_framework.pagination import LimitOffsetPagination

            self._paginator = LimitOffsetPagination()
            self._paginator.default_limit = 12
        return self._paginator

    def list(self, request, code, module_name):
        """
        查询部署历史
        - /api/bkapps/applications/{code}/operations/lists/
        - get param: environment, 发布的环境, string
        - get param: operator, 操作者, string
        - get param: limit, 结果数量, integer
        - get param: offset, 翻页跳过数量, integer
        """
        application = self.get_application()
        module = application.get_module(module_name)

        serializer = QueryOperationsSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.data

        operations = ModuleEnvironmentOperations.objects.owned_by_module(
            module, environment=params.get('environment')
        ).order_by('-created')

        # Filter by operator if provided
        operator = params.get('operator')
        if operator:
            operator = user_id_encoder.encode(settings.USER_TYPE, operator)
            operations = operations.filter(operator=operator)

        # Paginator
        page = self.paginator.paginate_queryset(operations, self.request, view=self)
        serializer = OperationSLZ(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)


class ProcessResourceMetricsViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """进程资源使用 Metrics API"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @staticmethod
    def _format_datetime(date_string):
        # front page should follow this format
        return datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")

    @swagger_auto_schema(query_serializer=ResourceMetricsSLZ)
    def list(self, request, code, module_name, environment):
        """获取 instance metrics"""
        wl_app = self.get_wl_app_via_path()
        serializer = ResourceMetricsSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        params = {
            'wl_app': wl_app,
            'process_type': data['process_type'],
            'query_metrics': data['query_metrics'],
            'time_range': MetricSmartTimeRange.from_request_data(data),
        }

        if data.get('instance_name'):
            params['instance_name'] = data['instance_name']
            get_metrics_method = list_app_proc_metrics
            ResultSLZ = ResourceMetricsResultSerializer
        else:
            get_metrics_method = list_app_proc_all_metrics  # type: ignore
            ResultSLZ = InstanceMetricsResultSerializer

        try:
            result = get_metrics_method(**params)
        except RequestMetricBackendError as e:
            raise error_codes.CANNOT_FETCH_RESOURCE_METRICS.f(str(e))
        except AppInstancesNotFoundError as e:
            raise error_codes.CANNOT_FETCH_RESOURCE_METRICS.f(str(e))
        except AppMetricNotSupportedError as e:
            raise error_codes.APP_METRICS_UNSUPPORTED.f(str(e))

        return Response(data={'result': ResultSLZ(instance=result, many=True).data})


class CustomDomainsConfigViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(tags=['访问入口'], responses={200: CustomDomainsConfigSLZ(many=True)})
    def retrieve(self, request, code):
        """查看独立域名相关配置信息，比如前端负载均衡 IP 地址等"""
        application = self.get_application()

        custom_domain_configs = []
        for module in application.modules.all():
            for env in module.envs.all():
                cluster = EnvClusterService(env).get_cluster()
                # `cluster` could be None when application's engine was disabled
                frontend_ingress_ip = cluster.ingress_config.frontend_ingress_ip if cluster else ''
                custom_domain_configs.append(
                    {
                        'module': module.name,
                        'environment': env.environment,
                        'frontend_ingress_ip': frontend_ingress_ip,
                    }
                )

        return Response(CustomDomainsConfigSLZ(custom_domain_configs, many=True).data)


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


class ConfigVarBuiltinViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """View the built-in environment variables of the app"""

    def _get_enum_choices_dict(self, EnumObj) -> Dict[str, str]:
        return {field[0]: field[1] for field in EnumObj.get_choices()}

    def get_builtin_envs_for_app(self, request, code):
        env_dict = self._get_enum_choices_dict(AppInfoBuiltinEnv)
        return Response(add_prefix_to_key(env_dict, settings.CONFIGVAR_SYSTEM_PREFIX))

    def get_builtin_envs_bk_platform(self, request, code):
        bk_address_envs = generate_env_vars_for_bk_platform(settings.CONFIGVAR_SYSTEM_PREFIX)

        application = self.get_application()
        region = application.region
        # 默认展示正式环境的环境变量
        environment = AppEnvironment.PRODUCTION.value
        envs_by_region_and_env = generate_env_vars_by_region_and_env(
            region, environment, settings.CONFIGVAR_SYSTEM_PREFIX
        )

        return Response({**bk_address_envs, **envs_by_region_and_env})

    def get_runtime_envs(self, request, code):
        env_dict = self._get_enum_choices_dict(AppRunTimeBuiltinEnv)
        envs = add_prefix_to_key(env_dict, settings.CONFIGVAR_SYSTEM_PREFIX)

        no_prefix_envs = self._get_enum_choices_dict(NoPrefixAppRunTimeBuiltinEnv)
        return Response({**envs, **no_prefix_envs})
