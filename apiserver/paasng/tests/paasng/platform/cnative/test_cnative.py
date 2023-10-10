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
from contextlib import nullcontext as does_not_raise

import pytest
from blue_krill.web.std_error import APIError

from paasng.platform.cnative.services import get_default_cluster_name
from tests.conftest import CLUSTER_NAME_FOR_TESTING
from tests.utils.mocks.engine import mock_cluster_service

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "data, region, ctx, expected",
    [
        (
            {"_lookup_field": "region", "data": {"default": CLUSTER_NAME_FOR_TESTING}},
            "default",
            does_not_raise(),
            CLUSTER_NAME_FOR_TESTING,
        ),
        (CLUSTER_NAME_FOR_TESTING, "default", does_not_raise(), CLUSTER_NAME_FOR_TESTING),
        (CLUSTER_NAME_FOR_TESTING, "404", does_not_raise(), CLUSTER_NAME_FOR_TESTING),
        # 集群不存在
        ("not-default", "default", pytest.raises(APIError), ""),
        # 对应 region 未配置 default cluster name
        ({"_lookup_field": "region", "data": {"default": "default"}}, "404", pytest.raises(APIError), ""),
    ],
)
def test_get_default_cluster_name(settings, data, region, ctx, expected):
    settings.CLOUD_NATIVE_APP_DEFAULT_CLUSTER = data

    with ctx, mock_cluster_service():
        assert get_default_cluster_name(region) == expected
