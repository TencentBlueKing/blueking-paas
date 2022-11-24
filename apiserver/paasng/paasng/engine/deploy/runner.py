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

from paasng.engine.constants import RuntimeType
from paasng.engine.deploy.building import start_build, start_build_error_callback
from paasng.engine.deploy.image import deploy_image
from paasng.engine.models.deployment import Deployment
from paasng.engine.signals import pre_appenv_deploy
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.specs import ModuleSpecs

logger = logging.getLogger(__name__)


class DeployTaskRunner:
    def __init__(self, deployment: Deployment):
        self.deployment = deployment
        self.module = deployment.app_environment.module

    def start(self):
        pre_appenv_deploy.send(self.deployment.app_environment, deployment=self.deployment)

        deployment_id = self.deployment.id
        logger.debug('Starting new deployment: %s for Module: %s...', deployment_id, self.module)
        if self.require_build():
            start_build.apply_async(args=(deployment_id,), link_error=start_build_error_callback.s())
        else:
            # TODO: deploy_image 修改成更符合 not require_build 的名称
            deploy_image.apply_async(args=(deployment_id,))

    def require_build(self) -> bool:
        if ModuleSpecs(self.module).runtime_type == RuntimeType.CUSTOM_IMAGE:
            return False
        elif (
            self.module.get_source_origin() == SourceOrigin.S_MART
            and self.deployment.version_info.version_type == "image"
        ):
            return False
        return True
