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

from paasng.platform.engine.handlers import update_last_deployed_date  # noqa: F401
from paasng.platform.engine.signals import post_appenv_deploy

from .setup_utils import create_fake_deployment

pytestmark = pytest.mark.django_db


def test_update_last_deployed_date(bk_module):
    """update_last_deployed_date will be triggered by event"""
    # Reset `last_deployed_date` field
    bk_module.last_deployed_date = None
    bk_module.save()
    bk_module.application.last_deployed_date = None
    bk_module.application.save()

    deployment = create_fake_deployment(bk_module)
    post_appenv_deploy.send(deployment.app_environment, deployment=deployment)

    bk_module.refresh_from_db()
    assert bk_module.last_deployed_date is not None
    assert bk_module.application.last_deployed_date is not None
