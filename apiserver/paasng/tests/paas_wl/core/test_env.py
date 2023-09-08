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
import pytest

from paas_wl.core.env import env_is_running
from tests.paas_wl.cnative.specs.utils import create_cnative_deploy
from tests.paas_wl.workloads.conftest import create_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestEnvIsRunning:
    def test_default_app_env_is_running(self, bk_app, bk_stag_env, bk_user, with_wl_apps):
        assert env_is_running(bk_stag_env) is False
        # Create a failed release at first, it should not affect the result
        create_release(bk_stag_env, bk_user, failed=True)
        assert env_is_running(bk_stag_env) is False

        create_release(bk_stag_env, bk_user, failed=False)
        assert env_is_running(bk_stag_env) is True

        # Simulate case when stag environment was offline
        bk_stag_env.is_offlined = True
        bk_stag_env.save()
        assert env_is_running(bk_stag_env) is False

    def test_cnative_app_env_is_running(self, bk_cnative_app, bk_stag_env, bk_user):
        assert env_is_running(bk_stag_env) is False

        create_cnative_deploy(bk_stag_env, bk_user)
        assert env_is_running(bk_stag_env) is True

        # Simulate case when stag environment was offline
        bk_stag_env.is_offlined = True
        bk_stag_env.save()
        assert env_is_running(bk_stag_env) is False
