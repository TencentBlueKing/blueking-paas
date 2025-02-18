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
from unittest import mock

import pytest
from rest_framework.reverse import reverse

from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("data", "status_code"),
    [
        (
            {
                "id": generate_random_string(length=10, chars=string.ascii_lowercase),
                "name": generate_random_string(length=20, chars=string.ascii_lowercase),
                "template": "foo",
                "creator": "user1",
                "repository": "http://git.example.com/template.git",
            },
            201,
        ),
        (
            {
                "id": generate_random_string(length=10, chars=string.ascii_lowercase),
                "name": generate_random_string(length=20, chars=string.ascii_lowercase),
                "template": "foo",
                "creator": "user1",
                "repository": "http://git.example.com/template.git",
                "extra_fields": {"email": "foo@example.com", "distributor_codes": ["1", "2"]},
            },
            201,
        ),
        (
            {
                "id": "invalid_id",
                "name": "2",
                "template": "foo",
                "creator": "user1",
                "repository": "http://git.example.com/template.git",
            },
            400,
        ),
    ],
)
def test_creat_api(sys_api_client, pd, data, status_code):
    url = reverse("sys.api.plugins_center.bk_plugins.create", kwargs={"pd_id": pd.identifier})
    with mock.patch("paasng.bk_plugins.pluginscenter.sys_apis.views.shim.setup_builtin_grade_manager"), mock.patch(
        "paasng.bk_plugins.pluginscenter.sys_apis.views.shim.setup_builtin_user_groups"
    ), mock.patch("paasng.bk_plugins.pluginscenter.sys_apis.views.shim.add_role_members"):
        response = sys_api_client.post(url, data=data)
        assert response.status_code == status_code
        if status_code == 201:
            assert response.data["publisher"] == data["creator"]
            assert response.data["repository"] == data["repository"]
