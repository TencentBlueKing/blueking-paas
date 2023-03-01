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
from unittest import mock

import pytest

from paasng.engine.controller.cluster import RegionClusterService

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def helper(bk_app):
    # Make a mocked controller client
    mocked_client = mock.Mock()
    mocked_client.list_region_clusters.return_value = [
        {
            "name": "default",
            "is_default": True,
            "bcs_cluster_id": "BCS-K8S-10000",
            "support_bcs_metrics": False,
            "ingress_config": {
                "app_root_domains": [{"name": "local-bkapps-t.example.com"}],
            },
        },
        {
            "name": "extra-1",
            "is_default": False,
            "bcs_cluster_id": "BCS-K8S-10001",
            "support_bcs_metrics": False,
            "ingress_config": {
                "app_root_domains": [{"name": "local-bkapps-extra.example.com"}],
            },
        },
    ]
    return RegionClusterService(bk_app, client=mocked_client)


class TestGetEngineAppCluster:
    def test_empty_cluster_field(self, bk_stag_env, helper):
        engine_app = bk_stag_env.engine_app
        assert helper.get_engine_app_cluster(engine_app.name).name == 'default'

    def test_valid_cluster_field(self, bk_stag_env, helper):
        engine_app = bk_stag_env.engine_app
        assert helper.get_engine_app_cluster(engine_app.name).name == 'extra-1'

    def test_invalid_cluster_field(self, bk_stag_env, helper):
        engine_app = bk_stag_env.engine_app
        with pytest.raises(ValueError):
            helper.get_engine_app_cluster(engine_app.name)


def test_get_cluster(helper):
    assert helper.get_cluster('extra-1').name == 'extra-1'
