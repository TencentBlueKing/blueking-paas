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
from typing import Dict, Optional

from paas_wl.bk_app.cnative.specs.models import AppModelResource
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import OperationTypes, ReplicasPolicy, RuntimeType
from paasng.platform.engine.deploy.building import start_build, start_build_error_callback
from paasng.platform.engine.deploy.image_release import release_without_build
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.operations import ModuleEnvironmentOperations
from paasng.platform.engine.signals import pre_appenv_deploy
from paasng.platform.engine.utils.query import get_latest_deploy_options
from paasng.platform.engine.utils.source import get_source_dir
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.sourcectl.constants import VersionType
from paasng.platform.sourcectl.models import VersionInfo
from paasng.platform.sourcectl.version_services import get_version_service

logger = logging.getLogger(__name__)


def initialize_deployment(
    env: "ModuleEnvironment",
    operator: str,
    version_info: VersionInfo,
    advanced_options: Optional[Dict] = None,
) -> Deployment:
    """初始化 Deployment 对象, 并记录该次部署事件.

    :param env: 需要部署的模块
    :param operator: 当前 operator 的 user id
    :param version_info: 需要部署的源码版本信息
    :param advanced_options: AdvancedOptionsField, 部署的高级选项.
    """
    module: Module = env.module
    application = module.application
    if module.build_config.build_method == RuntimeType.CUSTOM_IMAGE:
        source_location = ""
    elif advanced_options and (build_id := advanced_options.get("build_id")):
        # 选择已构建的镜像部署，则直接从上次构建对应的 Deployment 中获取 源码仓库地址
        # 查询第一个引用 build_id 的 Deployment
        ref = Deployment.objects.filter(build_id=build_id).order_by("created").first()
        # Note: views 已判断 Deployment 存在, 理论上这里并不会抛异常
        if not ref:
            raise ValueError(f"No build found for build_id: {build_id}")
        source_location = ref.source_location
    else:
        version_service = get_version_service(module, operator=operator)
        source_location = version_service.build_url(version_info)

    bkapp_revision_id = None
    if application.type == ApplicationType.CLOUD_NATIVE:
        # Get current module resource object
        model_resource, _ = AppModelResource.objects.get_or_create_by_module(module)
        bkapp_revision_id = model_resource.revision.id

    # 使用最新的部署选项
    deploy_options = get_latest_deploy_options(application)
    deployment = Deployment.objects.create(
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
            replicas_policy=deploy_options.replicas_policy if deploy_options else ReplicasPolicy.APP_DESC_PRIORITY,
        ),
        bkapp_revision_id=bkapp_revision_id,
        tenant_id=module.tenant_id,
    )
    deployment.refresh_from_db()
    ModuleEnvironmentOperations.objects.create(
        operator=deployment.operator,
        app_environment=env,
        application=application,
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
        logger.debug("Starting new deployment: %s for Module: %s...", deployment_id, self.module)
        if self.require_build():
            start_build.apply_async(args=(deployment_id, self.runtime_type), link_error=start_build_error_callback.s())
        else:
            release_without_build.apply_async(args=(deployment_id,))

    def require_build(self) -> bool:
        if self.runtime_type == RuntimeType.CUSTOM_IMAGE:  # noqa: SIM114
            return False
        elif (
            self.module.get_source_origin() == SourceOrigin.S_MART
            and self.deployment.version_info.version_type == VersionType.TAG.value
        ):
            return False
        # 如部署时指定了 build_id, 说明是选择了历史版本(镜像)进行发布, 则无需构建
        return not bool(self.deployment.advanced_options.build_id)
