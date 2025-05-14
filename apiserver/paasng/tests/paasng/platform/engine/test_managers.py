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

import pytest

from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.managers import DeployOperationManager
from paasng.platform.engine.models.offline import OfflineOperation

pytestmark = pytest.mark.django_db


class TestDeployOperationManager:
    def test_normal_pending_exist(self, bk_module):
        manager = DeployOperationManager(bk_module)
        d = Deployment.objects.create(app_environment=bk_module.get_envs("stag"))
        assert manager.has_pending()

        d.delete()
        OfflineOperation.objects.create(app_environment=bk_module.get_envs("stag"))
        assert manager.has_pending()

    def test_both_pending_exist(self, bk_module):
        manager = DeployOperationManager(bk_module)
        Deployment.objects.create(app_environment=bk_module.get_envs("stag"))
        OfflineOperation.objects.create(app_environment=bk_module.get_envs("stag"))

        assert manager.has_pending()

    def test_none_pending_exist(self, bk_module):
        manager = DeployOperationManager(bk_module)
        assert not manager.has_pending()
