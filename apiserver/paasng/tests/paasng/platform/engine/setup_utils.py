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

from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.models.deployment import AdvancedOptions
from paasng.platform.modules.models.deploy_config import Hook, HookList


def create_fake_deployment(module, app_environment="prod", operator=None, **kwargs):
    """Create a faked deployment objects

    :param app_environment: environment name, default to 'prod'
    :param operator: operator, default to owner of application
    :param kwargs: extra fields
    """
    application = module.application
    operator = operator or application.owner

    hooks = HookList(
        Hook(
            type=hook.type,
            command=hook.proc_command,
            enabled=hook.enabled,
        )
        for hook in module.deploy_hooks.all()
    )
    return Deployment.objects.create(
        region=application.region,
        operator=operator,
        app_environment=module.get_envs(app_environment),
        source_type=module.source_type,
        source_location="svn://local-svn/app/trunk",
        source_revision="1000",
        source_version_type="trunk",
        source_version_name="trunk",
        advanced_options=AdvancedOptions(),
        procfile={
            proc_spec.name: proc_spec.get_proc_command()
            for proc_spec in ModuleProcessSpec.objects.filter(module=module)
        },
        processes={
            proc_spec.name: {"name": proc_spec.name, "command": proc_spec.get_proc_command()}
            for proc_spec in ModuleProcessSpec.objects.filter(module=module)
        },
        hooks=deepcopy(hooks),
        **kwargs,
    )
