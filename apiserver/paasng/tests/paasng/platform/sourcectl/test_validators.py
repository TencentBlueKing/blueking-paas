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
from django.test.utils import override_settings

from paasng.platform.sourcectl.validators import validate_image_url


@pytest.mark.parametrize(
    ("url", "repo_info"),
    [
        pytest.param(
            "127.0.0.1:5000/library/python",
            {"DEFAULT_REGISTRY": "127.0.0.1:5001/library/python", "ALLOW_THIRD_PARTY_REGISTRY": False},
            marks=pytest.mark.xfail,
        ),
        ("127.0.0.1:5000/library/python", {"DEFAULT_REGISTRY": "127.0.0.1:5000", "ALLOW_THIRD_PARTY_REGISTRY": True}),
    ],
)
def test_validate_image_url(url, repo_info):
    with override_settings(DOCKER_REGISTRY_CONFIG=repo_info):
        assert validate_image_url(url, "dummy") == url
