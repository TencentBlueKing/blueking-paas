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

import os
from urllib.parse import urlparse

import pytest

from paasng.utils.moby_distribution.registry.client import DockerRegistryV2Client
from paasng.utils.moby_distribution.spec.endpoint import APIEndpoint


@pytest.fixture
def registry_endpoint():
    return os.getenv("UNITTEST_REGISTRY_HOST")


@pytest.fixture
def registry_netloc(registry_endpoint):
    if registry_endpoint is None:
        pytest.skip("integration not setup.")
    return urlparse(registry_endpoint).netloc


@pytest.fixture(autouse=True)
def setup(registry_endpoint):
    if registry_endpoint is None:
        pytest.skip("integration not setup.")


@pytest.fixture
def registry_client(registry_endpoint):
    return DockerRegistryV2Client.from_api_endpoint(APIEndpoint(url=registry_endpoint))
