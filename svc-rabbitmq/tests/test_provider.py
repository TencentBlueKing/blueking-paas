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

from unittest.mock import MagicMock, patch

import pytest
from vendor.provider import Provider

from .conftest import make_cluster


class TestProviderPickCluster:
    """pick_cluster: fallback from flat fields vs. weighted clusters list."""

    def test_from_flat_fields(self):
        provider = Provider(
            host="10.0.0.1",
            port=5672,
            management_api="http://10.0.0.1:15672",
            admin="admin",
            password="secret",
            version="3.9.0",
        )
        cluster = provider.pick_cluster()
        assert cluster.host == "10.0.0.1"
        assert cluster.version == "3.9.0"

    def test_raises_on_invalid_flat_fields(self):
        provider = Provider(host="10.0.0.1")
        with pytest.raises(ValueError, match="cluster 配置不正确"):
            provider.pick_cluster()

    def test_from_clusters_list(self):
        provider = Provider(
            clusters=[
                {
                    "weight": 100,
                    "values": {
                        "host": "10.0.0.2",
                        "port": 5672,
                        "management_api": "http://10.0.0.2:15672",
                        "admin": "admin",
                        "password": "secret",
                        "version": "3.8.0",
                    },
                }
            ]
        )
        cluster = provider.pick_cluster()
        assert cluster.host == "10.0.0.2"


class TestProviderResolveClusterPK:
    """resolve_cluster_pk: match by management_api or fallback to host/port."""

    def _db_cluster(self, pk, management_api, host="127.0.0.1", port=5672):
        obj = MagicMock()
        obj.pk = pk
        obj.management_api = management_api
        obj.host = host
        obj.port = port
        return obj

    @patch("vendor.provider.ClusterModel.objects")
    def test_match_by_management_api(self, mock_objects):
        db_cluster = self._db_cluster(pk=42, management_api="http://10.0.0.1:15672/")
        mock_objects.filter.return_value = [db_cluster]

        cluster = make_cluster(management_api="http://10.0.0.1:15672")
        assert Provider().resolve_cluster_pk(cluster) == 42

    @patch("vendor.provider.ClusterModel.objects")
    def test_returns_none_when_no_match(self, mock_objects):
        db_cluster = self._db_cluster(pk=1, management_api="http://other:15672")
        mock_objects.filter.return_value = [db_cluster]

        cluster = make_cluster(management_api="http://10.0.0.1:15672")
        assert Provider().resolve_cluster_pk(cluster) is None
