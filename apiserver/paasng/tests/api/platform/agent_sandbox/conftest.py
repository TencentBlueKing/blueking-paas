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
import uuid
from collections.abc import Generator
from typing import Any

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture(scope="session", autouse=True)
def _skip_if_old_k8s_version(skip_if_old_k8s_version):
    """Auto-apply shared k8s version skip guard for api agent_sandbox tests."""


@pytest.fixture()
def sandbox_id(api_client: APIClient, bk_app: Any) -> Generator[str, None, None]:
    """Create an available sandbox via API and return sandbox UUID for tests."""
    # Create the sandbox before test execution.
    create_url = reverse("agent_sandbox.create", kwargs={"code": bk_app.code})
    sandbox_name = f"api-sbx-{uuid.uuid4().hex[:8]}"
    create_resp = api_client.post(create_url, data={"name": sandbox_name})
    assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.json()

    value = create_resp.json()["uuid"]
    yield value

    # Destroy the created sandbox after test execution.
    destroy_url = reverse("agent_sandbox.destroy", kwargs={"sandbox_id": value})
    api_client.delete(destroy_url)
