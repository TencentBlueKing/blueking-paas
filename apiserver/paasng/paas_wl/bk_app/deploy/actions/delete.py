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

from django.db import models, transaction

from paas_wl.bk_app.applications.models import BuildProcess, WlApp
from paas_wl.bk_app.cnative.specs.models import AppModelDeploy, AppModelResource, AppModelRevision
from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.bk_app.processes.models import ProcessSpec
from paas_wl.core.env import env_is_running
from paas_wl.workloads.networking.ingress.models import Domain
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


def delete_env_resources(env: "ModuleEnvironment"):
    """Delete app's resources in cluster"""
    if not env_is_running(env):
        return

    wl_app = env.wl_app
    NamespacesHandler.new_by_app(wl_app).delete(namespace=wl_app.namespace)
    return


def delete_module_related_res(module: "Module"):
    """Delete module's related resources"""
    with transaction.atomic(using="default"), transaction.atomic(using="workloads"):
        _delete_module_related_res(module)
        # Delete related EngineApp db records
        for env in module.get_envs():
            env.get_engine_app().delete()


def _delete_module_related_res(module: Module) -> None:
    """Delete all related resources of module"""
    # Remove module level data
    model_cls: models.Model
    for model_cls in [Domain, AppModelDeploy, AppModelResource, AppModelRevision]:
        model_cls.objects.filter(module_id=module.id).delete()

    # Environment/EngineApp level data
    for env in module.get_envs():
        # Manually remove data which don't has a foreign key relation
        ProcessSpec.objects.filter(engine_app_id=env.engine_app_id).delete()
        # Remove OutputStream manually because there is no backward foreign key
        # relationship.
        for bp in BuildProcess.objects.filter(app__uuid=env.engine_app_id):
            bp.output_stream.delete()

        # Delete WlApp and it's related resources and models
        try:
            wl_app = WlApp.objects.get(pk=env.engine_app_id)
        except WlApp.DoesNotExist:
            continue

        # Delete all resources in cluster, allow failure
        try:
            delete_env_resources(env)
        except Exception as e:
            logger.warning("Error deleting app cluster resources, app: %s, error: %s", wl_app, e)

        # This will also remove cascaded models:
        # Build, BuildProcess, Config, Release, AppMetricsMonitor, AppImageCredential,
        # AppAddOn, AppDomain, AppSubpath.
        wl_app.delete()
