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
import uuid
from contextlib import nullcontext as does_not_raise
from unittest import mock

import pytest
from blue_krill.web.std_error import APIError

from paasng.cnative.services import get_default_cluster_name, initialize_simple

pytestmark = pytest.mark.django_db


def test_initialize_simple(settings, bk_cnative_app, mock_current_engine_client):
    settings.CLOUD_NATIVE_APP_DEFAULT_CLUSTER = "default"
    module = bk_cnative_app.get_default_module()
    assert module.envs.count() == 0
    with mock.patch('paasng.cnative.services.controller_client') as mocker:
        mocker.app__create.side_effect = lambda region, app_name, app_type: {"uuid": str(uuid.uuid4())}

        initialize_simple(module, data={'image': 'nginx:latest'})
        assert mocker.create_cnative_app_model_resource.called
        args = mocker.create_cnative_app_model_resource.call_args[0]
        assert module.region == args[0]
        assert 'image' in args[1]
        assert module.envs.count() == 2
    # 验证 get_engine_app_via_path 可获取到 EngineApp 实例
    assert module.get_envs("stag").engine_app is not None


@pytest.mark.parametrize(
    "data, region, ctx, expected",
    [
        ({"_lookup_field": "region", "data": {"default": "default"}}, "default", does_not_raise(), "default"),
        ("default", "default", does_not_raise(), "default"),
        ("default", "404", does_not_raise(), "default"),
        # 集群不存在
        ("not-default", "default", pytest.raises(APIError), ""),
        # 对应 region 未配置 default cluster name
        ({"_lookup_field": "region", "data": {"default": "default"}}, "404", pytest.raises(APIError), ""),
    ],
)
def test_get_default_cluster_name(mock_current_engine_client, settings, data, region, ctx, expected):
    settings.CLOUD_NATIVE_APP_DEFAULT_CLUSTER = data

    with ctx:
        assert get_default_cluster_name(region) == expected
