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

from typing import Optional

from django.conf import settings

from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.models import Deployment, DeployOptions, OfflineOperation
from paasng.platform.engine.workflow import DeploymentCoordinator


class DeploymentGetter:
    """Getter to get meaningful Deployment obj of `env`"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def get_latest_deployment(self) -> Optional[Deployment]:
        """返回最后创建的 Deployment, 如果应用未部署过, 则返回 None"""
        try:
            return self.env.deployments.latest("created")
        except Deployment.DoesNotExist:
            return None

    def get_latest_succeeded(self) -> Optional[Deployment]:
        """返回最后部署成功的 Deployment, 如未曾部署成功或环境已下架, 则返回 None"""
        try:
            deployment = self.env.deployments.latest_succeeded()
        except Deployment.DoesNotExist:
            return None
        if self.env.is_offlined:
            return None
        return deployment

    def get_current_deployment(self) -> Optional[Deployment]:
        """返回当前在部署的 Deployment, 如无 Deployment 正在部署, 则返回 None"""
        return DeploymentCoordinator(env=self.env).get_current_deployment()


class OfflineOperationGetter:
    """Getter to get meaningful OfflineOperation obj of `env`"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def get_latest_operation(self) -> Optional[OfflineOperation]:
        """返回最后创建的 OfflineOperation, 如果应用未下架过, 则返回 None"""
        try:
            return self.env.offlines.latest("created")
        except OfflineOperation.DoesNotExist:
            return None

    def get_latest_succeeded(self) -> Optional[OfflineOperation]:
        """返回最后下架成功的 OfflineOperation, 如无模块已重新部署或未曾下架, 则返回 None"""
        try:
            operation = self.env.offlines.latest_succeeded()
        except OfflineOperation.DoesNotExist:
            return None
        if not self.env.is_offlined:
            return None
        return operation

    def get_current_operation(self) -> Optional[OfflineOperation]:
        """返回当前在下架的 OfflineOperation, 如无 Deployment 正在部署, 则返回 None"""
        try:
            return self.env.offlines.get_latest_resumable(max_resumable_seconds=settings.ENGINE_OFFLINE_RESUMABLE_SECS)
        except OfflineOperation.DoesNotExist:
            return None


def get_latest_deploy_options(app: Application) -> DeployOptions | None:
    """获取应用最新的 deploy_options"""
    return app.deploy_options.order_by("-updated").first()
