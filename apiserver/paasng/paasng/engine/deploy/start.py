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
import logging
from copy import deepcopy
from typing import Dict, Optional

from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.dev_resources.sourcectl.version_services import get_version_service
from paasng.engine.constants import OperationTypes, RuntimeType
from paasng.engine.deploy.building import start_build, start_build_error_callback
from paasng.engine.deploy.image_release import deploy_image
from paasng.engine.models.deployment import Deployment
from paasng.engine.models.operations import ModuleEnvironmentOperations
from paasng.engine.signals import pre_appenv_deploy
from paasng.engine.utils.source import get_source_dir
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.platform.modules.specs import ModuleSpecs

logger = logging.getLogger(__name__)


def initialize_deployment(
    env: 'ModuleEnvironment', operator: str, version_info: VersionInfo, advanced_options: Optional[Dict] = None
) -> Deployment:
    """初始化 Deployment 对象, 并记录该次部署事件.

    :param env: 需要部署的模块
    :param operator: 当前 operator 的 user id
    :param version_info: 需要部署的源码版本信息
    :param advanced_options: AdvancedOptionsField, 部署的高级选项.
    """
    module: Module = env.module
    version_service = get_version_service(module, operator=operator)
    source_location = version_service.build_url(version_info)

    deploy_config = module.get_deploy_config()
    deployment = Deployment.objects.create(
        region=module.region,
        operator=operator,
        app_environment=env,
        source_type=module.source_type,
        source_location=source_location,
        source_revision=version_info.revision,
        source_version_type=version_info.version_type,
        source_version_name=version_info.version_name,
        advanced_options=dict(
            **(advanced_options or {}),
            source_dir=get_source_dir(module, operator=operator, version_info=version_info),
        ),
        hooks=deepcopy(deploy_config.hooks),
    )
    ModuleEnvironmentOperations.objects.create(
        operator=deployment.operator,
        app_environment=deployment.app_environment,
        application=deployment.app_environment.application,
        operation_type=OperationTypes.ONLINE.value,
        object_uid=deployment.pk,
    )
    return deployment


class DeployTaskRunner:
    """Start a deploy task.

    :param deployment: An initialized deployment object.
    """

    def __init__(self, deployment: Deployment):
        self.deployment = deployment
        self.module = deployment.app_environment.module
        self.runtime_type = ModuleSpecs(self.module).runtime_type

    def start(self):
        pre_appenv_deploy.send(self.deployment.app_environment, deployment=self.deployment)

        deployment_id = self.deployment.id
        logger.debug('Starting new deployment: %s for Module: %s...', deployment_id, self.module)
        if self.require_build():
            start_build.apply_async(args=(deployment_id, self.runtime_type), link_error=start_build_error_callback.s())
        else:
            # TODO: deploy_image 修改成更符合 not require_build 的名称
            deploy_image.apply_async(args=(deployment_id,))

    def require_build(self) -> bool:
        if self.runtime_type == RuntimeType.CUSTOM_IMAGE:
            return False
        elif (
            self.module.get_source_origin() == SourceOrigin.S_MART
            and self.deployment.version_info.version_type == "image"
        ):
            return False
        return True
