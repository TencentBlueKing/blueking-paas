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

import string

import pytest
from django.conf import settings

from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.scene_app.initializer import SceneAPPInitializer
from tests.utils import mock
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db


class TestSceneAPPInitializer:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from tests.utils.helpers import create_scene_tmpls

        create_scene_tmpls()
        with (
            mock.patch(
                "paasng.platform.declarative.application.controller.initialize_smart_module",
                return_value={},
            ),
            mock.patch(
                "paasng.platform.scene_app.initializer.create_oauth2_client",
                return_value="test_app_secret",
            ),
            mock.patch(
                "paasng.platform.scene_app.initializer.get_oauth2_client_secret",
                return_value="test_app_secret",
            ),
        ):
            yield

    def test_normal(self, bk_user):
        app_name = generate_random_string(8)
        app_code = generate_random_string(8, string.ascii_lowercase)
        app, sync_result = SceneAPPInitializer(
            bk_user,
            "scene_tmpl1",
            app_name,
            app_code,
            AppTenantMode.GLOBAL,
            "",
            DEFAULT_TENANT_ID,
            settings.DEFAULT_REGION_NAME,
            {
                "source_control_type": "github",
                "source_repo_url": "https://github.com/octocat/helloWorld.git",
                "source_repo_auth_info": {},
            },
        ).execute()
        assert app is not None
        assert app.code == app_code
        assert app.is_scene_app is True
        assert sync_result is not None
