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
"""Utilities related with application models"""
import logging

from django.db import models

from paas_wl.cnative.specs.models import AppModelDeploy, AppModelResource, AppModelRevision
from paas_wl.networking.ingress.models import Domain
from paas_wl.platform.applications.models import BuildProcess, EngineApp
from paas_wl.platform.applications.struct_models import Module, get_structured_app
from paas_wl.resources.actions.delete import delete_app_resources
from paas_wl.workloads.processes.models import ProcessSpec

logger = logging.getLogger(__name__)


def delete_module_related_res(module: Module) -> None:
    """Delete all related resources of module"""
    app = get_structured_app(code=module.application.code)

    # Remove module level data
    model_cls: models.Model
    for model_cls in [Domain, AppModelDeploy, AppModelResource, AppModelRevision]:
        model_cls.objects.filter(module_id=module.id).delete()

    # Environment/EngineApp level data
    for env in app.get_envs_by_module(module):
        # Manually remove data which don't has a foreign key relation
        ProcessSpec.objects.filter(engine_app_id=env.engine_app_id).delete()
        # Remove OutputStream manually because there is no backward foreign key
        # relationship.
        for bp in BuildProcess.objects.filter(app__uuid=env.engine_app_id):
            bp.output_stream.delete()

        # Delete EngineApp and it's related resources and models
        try:
            engine_app = EngineApp.objects.get(pk=env.engine_app_id)
        except EngineApp.DoesNotExist:
            continue

        # Delete all resources in cluster, allow failure
        try:
            delete_app_resources(engine_app)
        except Exception as e:
            logger.warning('Error deleting app cluster resources, app: %s, error: %s', engine_app, e)

        # This will also remove cascaded models:
        # Build, BuildProcess, Config, Release, AppMetricsMonitor, AppImageCredential,
        # AppAddOn, AppDomain, AppSubpath.
        engine_app.delete()
