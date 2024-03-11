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
from django.conf import settings

from paasng.accessories.devcontainer.config_var import generate_envs
from paasng.platform.engine.configurations.building import SlugbuilderInfo
from paasng.platform.engine.constants import AppInfoBuiltinEnv

pytestmark = pytest.mark.django_db


def test_generate_envs(bk_app, bk_module):
    envs = generate_envs(bk_app, bk_module)

    expected_env_keys = [
        f"{settings.CONFIGVAR_SYSTEM_PREFIX}{AppInfoBuiltinEnv.APP_SECRET}",
        f"{settings.CONFIGVAR_SYSTEM_PREFIX}{AppInfoBuiltinEnv.APP_ID}",
        "DEV_SERVER_ADDR",
    ]

    if settings.PYTHON_BUILDPACK_PIP_INDEX_URL:
        expected_env_keys.extend(["PIP_INDEX_URL", "PIP_INDEX_HOST"])

    build_info = SlugbuilderInfo.from_module(bk_module)
    if build_info.buildpacks_info:
        expected_env_keys.append("REQUIRED_BUILDPACKS")

    for k in expected_env_keys:
        assert k in envs
