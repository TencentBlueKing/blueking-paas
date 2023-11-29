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
from typing import List
from unittest import mock

import pytest

from paasng.infras.iam.permissions.apply_url import ApplyURLGenerator
from paasng.infras.iam.permissions.request import ActionResourcesRequest
from paasng.infras.iam.permissions.resources.application import ApplicationPermission

from .fake.application import FakeApplicationPermission


def generate_apply_url(username: str, action_request_list: List[ActionResourcesRequest]) -> str:
    expect = []
    for req in action_request_list:
        resources = ""
        if req.resources:
            resources = "".join(req.resources)

        expect.append(f"resource_type({req.resource_type}):action_id({req.action_id}):resources({resources}))")

    return " and ".join(expect)


@pytest.fixture(autouse=True)
def patch_generate_apply_url():
    with mock.patch.object(ApplyURLGenerator, "generate_apply_url", new=generate_apply_url):
        yield


@pytest.fixture
def app_permission_obj():
    patcher = mock.patch.object(ApplicationPermission, "__bases__", (FakeApplicationPermission,))
    with patcher:
        patcher.is_local = True  # 标注为本地属性，__exit__ 的时候恢复成 patcher.temp_original
        yield ApplicationPermission()
