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
from typing import Optional, Tuple

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.image_parser import ImageParser
from paas_wl.bk_app.cnative.specs.models import AppModelRevision
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.utils.query import DeploymentGetter, OfflineOperationGetter
from paasng.platform.modules.models import BuildConfig
from paasng.platform.sourcectl.models import VersionInfo

logger = logging.getLogger(__name__)


def get_env_deployed_version_info(env: ModuleEnvironment) -> Tuple[RuntimeType, Optional[VersionInfo]]:
    """get deployed version info of given env

    :return: build_method, version_info
    """
    application = env.application
    build_config = BuildConfig.objects.get_or_create_by_module(env.module)
    deployment = DeploymentGetter(env).get_latest_succeeded()
    if not deployment:
        logger.debug("Module: %s Env: %s is not deployed", env.module.name, env.environment)
        return build_config.build_method, None

    if OfflineOperationGetter(env).get_latest_succeeded() is not None:
        logger.debug("Module: %s Env: %s has been offline", env.module.name, env.environment)
        return build_config.build_method, None

    if application.type == ApplicationType.CLOUD_NATIVE and build_config.build_method == RuntimeType.CUSTOM_IMAGE:
        bkapp_revision = AppModelRevision.objects.get(pk=deployment.bkapp_revision_id)
        # TODO dirty code. V1ALPHA1 版本迁移后优化
        try:
            res = BkAppResource(**bkapp_revision.deployed_value)
            tag = ImageParser(res).get_tag()
        except ValueError:
            res = BkAppResource(**bkapp_revision.json_value)
            tag = ImageParser(res).get_tag()
        version_info = VersionInfo(revision="", version_name=tag or "--", version_type="tag")
    else:
        version_info = deployment.get_version_info()
    return build_config.build_method, version_info
