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
from unittest import mock

import pytest
from bkpaas_auth.models import User

from paas_wl.cnative.specs.constants import DeployStatus
from paas_wl.cnative.specs.models import AppModelDeploy, AppModelResource, create_app_resource
from paas_wl.cnative.specs.resource import deploy
from paas_wl.platform.applications.models.app import get_ns
from paas_wl.platform.applications.struct_models import ModuleEnv
from paas_wl.resources.base.kres import KNamespace
from paas_wl.resources.utils.basic import get_client_by_env
from tests.utils.mocks.platform import FakePlatformSvcClient


def create_cnative_deploy(env: ModuleEnv, user: User, status: DeployStatus = DeployStatus.READY) -> AppModelDeploy:
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


@pytest.fixture
def deploy_stag_env(bk_stag_env):
    """Deploy a default payload to cluster for stag environment"""
    app = bk_stag_env.application
    with mock.patch('paas_wl.platform.external.client._global_plat_client', new=FakePlatformSvcClient()), mock.patch(
        'paas_wl.cnative.specs.resource.KNamespace.wait_for_default_sa'
    ):
        resource = create_app_resource(app.name, 'nginx:latest')
        deploy(bk_stag_env, resource.to_deployable())
        yield

    # Clean up resource, delete entire namespace
    with get_client_by_env(bk_stag_env) as client:
        KNamespace(client).delete(get_ns(bk_stag_env))
