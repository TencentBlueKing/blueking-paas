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
from typing import List, Literal

from bkpaas_auth.models import User

from paas_wl.cnative.specs.constants import DeployStatus, MResConditionType, MResPhaseType
from paas_wl.cnative.specs.crd.bk_app import BkAppResource, MetaV1Condition
from paas_wl.cnative.specs.models import AppModelDeploy, AppModelResource, create_app_resource
from paasng.platform.applications.models import ModuleEnvironment


def create_cnative_deploy(
    env: ModuleEnvironment, user: User, status: DeployStatus = DeployStatus.READY
) -> AppModelDeploy:
    """Initialize an app's model resource and create a deployment instance under
    given environment.

    :param env: The ModuleEnv object
    :param status: The status of deploy, "READY" by default
    """
    app = env.application
    module = env.module
    resource = create_app_resource(app.name, 'nginx:latest')
    model_res = AppModelResource.objects.create_from_resource(app.region, str(app.id), str(module.id), resource)
    return AppModelDeploy.objects.create(
        application_id=app.id,
        module_id=module.id,
        environment_name=env.environment,
        name='default-deploy-1',
        revision=model_res.revision,
        status=status.value,
        operator=user,
    )


def create_condition(
    type_: MResConditionType,
    status: Literal["True", "False", "Unknown"] = "Unknown",
    reason: str = '',
    message: str = '',
) -> MetaV1Condition:
    return MetaV1Condition(
        type=type_,
        status=status,
        reason=reason,
        message=message,
    )


def create_res_with_conds(
    conditions: List[MetaV1Condition], phase: MResPhaseType = MResPhaseType.AppPending
) -> BkAppResource:
    mres = create_app_resource(name="foo", image="nginx:latest")
    mres.status.conditions = conditions
    mres.status.phase = phase
    return mres
