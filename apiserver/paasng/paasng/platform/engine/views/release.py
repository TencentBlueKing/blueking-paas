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

from typing import Dict, Optional

from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.bk_app.applications.api import get_latest_build_id
from paas_wl.bk_app.processes.processes import ProcessManager
from paasng.accessories.publish.entrance.exposer import env_is_deployed, get_exposed_url
from paasng.accessories.publish.entrance.preallocated import get_preallocated_url
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.engine.deploy.release.legacy import release_by_engine
from paasng.platform.engine.models.config_var import ENVIRONMENT_NAME_FOR_GLOBAL
from paasng.platform.engine.serializers import DeploymentSLZ, GetReleasedInfoSLZ, OfflineOperationSLZ
from paasng.platform.engine.utils.query import DeploymentGetter, OfflineOperationGetter
from paasng.utils.error_codes import error_codes
from paasng.utils.views import allow_resp_patch


class ReleasedInfoViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    serializer_class = GetReleasedInfoSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(deprecated=True)
    def get_current_info(self, request, code, module_name, environment):
        module_env = self.get_env_via_path()
        serializer = self.serializer_class(request.query_params)

        deployment = DeploymentGetter(module_env).get_latest_succeeded()
        if deployment is None:
            raise error_codes.APP_NOT_RELEASED

        entrance = get_exposed_url(deployment.app_environment)
        data = {
            "deployment": DeploymentSLZ(deployment).data,
            "exposed_link": {"url": entrance.address if entrance else None},
        }
        if serializer.data["with_processes"]:
            _specs = ProcessManager(module_env).list_processes_specs()
            # Change structure of "specs", make it compatible with frontend client
            specs = [{spec["name"]: spec} for spec in _specs]
            data["processes"] = specs
        return Response(data)

    @allow_resp_patch
    def get_current_state(self, request, code, module_name, environment):
        """
        - /api/bkapps/applications/{code}/envs/{environment}/deployments/latest/
        - path param: code, app名, 必须
        - path param: environment, 部署环境(stag或者prod), 必须
        - get param: with_processes, 是否返回进程信息，传递 true 时返回，默认不返回
        """
        module_env = self.get_env_via_path()
        serializer = self.serializer_class(request.query_params)

        deployment_data = None
        offline_data = None
        default_access_entrance = get_preallocated_url(module_env)

        if module_env.is_offlined:
            offline_operation = OfflineOperationGetter(module_env).get_latest_succeeded()
            if offline_operation is None:
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
            "deployment": deployment_data,
            "offline": offline_data,
            "exposed_link": {"url": exposed_link.address if exposed_link else None},
            "default_access_entrance": {"url": default_access_entrance.address if default_access_entrance else None},
        }
        if serializer.data["with_processes"]:
            _specs = ProcessManager(module_env).list_processes_specs()
            # Change structure of "specs", make it compatible with frontend client
            specs = [{spec["name"]: spec} for spec in _specs]
            data["processes"] = specs

        return Response(data)

    @staticmethod
    def get_deployment_data(env) -> Optional[Dict]:
        """Try to get the latest deployment data by querying Deployment model"""
        deployment = DeploymentGetter(env).get_latest_succeeded()
        if deployment is None:
            return None
        return DeploymentSLZ(deployment).data


class ReleasesViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def release(self, request, code, module_name, environment):
        """跳过构建，使用最近一次的构建产物发布应用。

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
            build_id = get_latest_build_id(application_env)
            if build_id:
                try:
                    release_by_engine(application_env, str(build_id))
                except ValueError:
                    raise error_codes.CANNOT_DEPLOY_APP.f(_("服务异常"))

        return Response(status=status.HTTP_201_CREATED)
