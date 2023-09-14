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
from copy import deepcopy

from paas_wl.platform.applications.models import WlApp
from paasng.engine.models import Deployment
from paasng.engine.models.deployment import AdvancedOptions


def create_fake_deployment(module, app_environment='prod', operator=None, **kwargs):
    """Create a faked deployment objects

    :param app_environment: environment name, default to 'prod'
    :param operator: operator, default to owner of application
    :param kwargs: extra fields
    """
    application = module.application
    operator = operator or application.owner

    deploy_config = module.get_deploy_config()
    deployment = Deployment.objects.create(
        region=application.region,
        operator=operator,
        app_environment=module.get_envs(app_environment),
        source_type=module.source_type,
        source_location='svn://local-svn/app/trunk',
        source_revision='1000',
        source_version_type='trunk',
        source_version_name='trunk',
        advanced_options=AdvancedOptions(),
        procfile=deploy_config.procfile.copy(),
        processes={k: {"name": k, "command": v} for k, v in deploy_config.procfile.items()},
        hooks=deepcopy(deploy_config.hooks),
        **kwargs
    )

    # bk_deployment.app_environment  外键未实例化，补全
    name = deployment.app_environment.engine_app.name
    region = deployment.app_environment.engine_app.region
    WlApp.objects.create(name=name, region=region)

    return deployment
