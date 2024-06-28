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

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.engine.deploy.bg_command.pre_release import ApplicationPreReleaseExecutor
from paasng.platform.engine.deploy.release.operator import BkAppReleaseMgr
from paasng.platform.engine.models.deployment import Deployment


def start_release_step(deployment_id: str):
    """start a release process"""
    deployment = Deployment.objects.get(pk=deployment_id)
    application = deployment.app_environment.application

    if application.type == ApplicationType.CLOUD_NATIVE:
        release_mgr = BkAppReleaseMgr.from_deployment_id(deployment_id)
    else:
        release_mgr = ApplicationPreReleaseExecutor.from_deployment_id(deployment_id)
    release_mgr.start()
