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

import builtins
from typing import Callable, List, Literal, Optional, Union

from bkpaas_auth.models import User

from paas_wl.bk_app.cnative.specs.constants import (
    BKPAAS_DEPLOY_ID_ANNO_KEY,
    DeployStatus,
    MResConditionType,
    MResPhaseType,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource, MetaV1Condition
from paas_wl.bk_app.cnative.specs.models import AppModelDeploy, AppModelResource, create_app_resource
from paasng.platform.applications.models import ModuleEnvironment


def create_cnative_deploy(
    env: ModuleEnvironment,
    user: User,
    status: DeployStatus = DeployStatus.READY,
    resource: Optional[BkAppResource] = None,
    name: str = "default-deploy-1",
) -> AppModelDeploy:
    """Initialize an app's model resource and create a deployment instance under
    given environment.

    :param env: The ModuleEnv object
    :param user: The owner object
    :param status: The status of deploy, "READY" by default
    :param resource: If not given, create a default one using the "nginx:latest" image
    :param name: The name of the deploy object, optional
    """
    app = env.application
    module = env.module
    if not resource:
        resource = create_app_resource(app.name, "nginx:latest")

    if not AppModelResource.objects.filter(module_id=str(module.id)).exists():
        model_res = AppModelResource.objects.create_from_resource(app.region, str(app.id), str(module.id), resource)
    else:
        # If the model resource already exists, use it directly and update the revision
        model_res = AppModelResource.objects.get(module_id=str(module.id))
        model_res.use_resource(resource)

    return AppModelDeploy.objects.create(
        application_id=app.id,
        module_id=module.id,
        environment_name=env.environment,
        name=name,
        revision=model_res.revision,
        status=status.value,
        operator=user,
    )


def create_condition(
    type_: MResConditionType,
    status: Literal["True", "False", "Unknown"] = "Unknown",
    reason: str = "",
    message: str = "",
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


def with_conds(conditions: List[MetaV1Condition], phase: MResPhaseType = MResPhaseType.AppPending):
    def apply(mres: BkAppResource):
        mres.status.conditions = conditions
        mres.status.phase = phase

    return apply


# can not import ellipsis from builtins directly, so we must wrap it with quotes
def with_deploy_id(deploy_id: str, status_deploy_id: Union[str, "builtins.ellipsis"] = Ellipsis):
    def apply(mres: BkAppResource):
        mres.metadata.annotations[BKPAAS_DEPLOY_ID_ANNO_KEY] = deploy_id
        if status_deploy_id is ...:
            mres.status.deployId = deploy_id
        else:
            mres.status.deployId = status_deploy_id
        return mres

    return apply


def create_res(*applys: Callable[[BkAppResource], None]):
    mres = create_app_resource(name="foo", image="nginx:latest")
    for apply in applys:
        apply(mres)
    return mres
