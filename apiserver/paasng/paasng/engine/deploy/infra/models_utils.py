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
"""Utilities related with models
"""
import logging
from copy import deepcopy
from typing import Dict, Optional

from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.dev_resources.sourcectl.version_services import get_version_service
from paasng.engine.constants import ImagePullPolicy, OperationTypes
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.deploy.infra.source import get_source_dir
from paasng.engine.helpers import RuntimeInfo
from paasng.engine.models import Deployment, EngineApp
from paasng.engine.models.operations import ModuleEnvironmentOperations
from paasng.platform.applications.models import ModuleEnvironment

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
    module = env.module
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


def update_engine_app_config(
    engine_app: EngineApp,
    version_info: VersionInfo,
    image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT,
):
    """Update engine app's configs by calling remote service"""
    runtime = RuntimeInfo(engine_app=engine_app, version_info=version_info)
    client = EngineDeployClient(engine_app)
    return client.update_config(
        runtime={
            "image": runtime.image,
            "type": runtime.type,
            "endpoint": runtime.endpoint,
            "image_pull_policy": image_pull_policy.value,
        },
    )


# TODO: Remove this function
def get_processes_by_build(engine_app: EngineApp, build_id: str) -> Dict[str, str]:
    engine_client = EngineDeployClient(engine_app)
    processes = engine_client.get_procfile(build_id)
    if not processes:
        raise RuntimeError("can't find processes in engine")
    return processes
