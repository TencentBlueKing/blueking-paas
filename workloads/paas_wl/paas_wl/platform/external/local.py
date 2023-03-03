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
import json
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

from paasng.engine.constants import JobStatus
from paasng.engine.deploy.release import ApplicationReleaseMgr
from paasng.engine.models import Deployment
from paasng.engine.models.offline import OfflineOperation
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.applications.signals import module_environment_offline_success
from paasng.platform.modules.models import Module
from paasng.platform.operations.models import Operation


class AppBasicSLZ(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'type', 'region', 'code', 'name']


class ModuleBasicSLZ(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'name']


class ModuleEnvBasicSLZ(serializers.ModelSerializer):
    engine_app_id = serializers.CharField(read_only=True)

    class Meta:
        model = ModuleEnvironment
        fields = ['id', 'environment', 'module_id', 'engine_app_id', 'is_offlined']


class LocalPlatformSvcClient:
    """Client for "apiserver" module, uses local module"""

    def query_applications(  # noqa: C901
        self,
        uuids: Optional[List[UUID]] = None,
        codes: Optional[List[str]] = None,
        module_id: Optional[UUID] = None,
        env_id: Optional[int] = None,
        engine_app_id: Optional[UUID] = None,
    ):
        """Query application's basic info by uuid(s), code(s), module_id, env_id,
        engine_app_id.

        :returns: list of basic application info
        :raises: PlatClientRequestError
        """
        indexes: List[Any]
        if codes:
            indexes = codes
            apps_map = {app.code: app for app in Application.default_objects.filter(code__in=codes)}
        elif uuids:
            indexes = uuids
            apps_map = {app.id: app for app in Application.default_objects.filter(id__in=indexes)}
        # Below conditions only allows a single query term
        elif module_id:
            indexes = [module_id]
            try:
                apps_map = {module_id: Module.objects.get(pk=module_id).application}
            except Module.DoesNotExist:
                apps_map = {}
        elif env_id:
            indexes = [env_id]
            try:
                apps_map = {env_id: ModuleEnvironment.objects.get(pk=env_id).application}
            except ModuleEnvironment.DoesNotExist:
                apps_map = {}
        elif engine_app_id:
            indexes = [engine_app_id]
            try:
                apps_map = {engine_app_id: ModuleEnvironment.objects.get(engine_app_id=engine_app_id).application}
            except ModuleEnvironment.DoesNotExist:
                apps_map = {}
        else:
            raise ValueError('params invalid')

        results: List[Union[None, Dict]] = []
        for idx in indexes:
            app = apps_map.get(idx)
            if not app:
                results.append(None)
                continue

            item = {'application': AppBasicSLZ(app).data}

            modules = Module.objects.filter(application=app)
            item['modules'] = ModuleBasicSLZ(modules, many=True).data

            envs = ModuleEnvironment.objects.filter(module__in=modules)
            item['envs'] = ModuleEnvBasicSLZ(envs, many=True).data
            results.append(item)

        # Return raw JSON data to be compatible
        return json.loads(JSONRenderer().render(results))

    def finish_release(self, deployment_id: str, status: str, error_detail: str):
        mgr = ApplicationReleaseMgr.from_deployment_id(deployment_id)
        mgr.callback_release(JobStatus(status), error_detail)

    def finish_archive(self, operation_id: str, status: str, error_detail: str):
        offline_op = OfflineOperation.objects.get(id=operation_id)
        if status == JobStatus.SUCCESSFUL:
            offline_op.set_successful()
        else:
            offline_op.set_failed(error_detail)

        module_environment_offline_success.send(
            sender=OfflineOperation, offline_instance=offline_op, environment=offline_op.app_environment.environment
        )

    def retrieve_deployment(self, deployment_id: str) -> Deployment:
        return Deployment.objects.get(pk=deployment_id)

    def create_operation_log(
        self,
        env: ModuleEnvironment,
        operate_type: int,
        operator: str,
        extra_values: Optional[Dict] = None,
    ):
        """Create an operation log for application

        :returns: None if creation succeeded
        :raises: PlatClientRequestError
        """
        Operation.objects.create(
            application=env.application,
            type=operate_type,
            user=operator,
            region=env.application.region,
            module_name=env.module.name,
            source_object_id=str(env.id),
            extra_values=extra_values,
        )
