# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from unittest.mock import patch

import pytest
from paas_service.base_vendor import ArgumentInvalidError, InstanceData, OperationFailed
from vendor.cluster_tag_selector import ClusterTagSelector
from vendor.models import Cluster as ClusterModel
from vendor.models import ClusterTag, InstanceBill
from vendor.provider import Provider


def create_db_cluster(name, tags=(), enable=True, extra=None) -> ClusterModel:
    cluster = ClusterModel.objects.create(
        name=name,
        host=f"{name}.example.com",
        port=5672,
        management_api=f"http://{name}.example.com:15672",
        admin="admin",
        password="secret",
        version="3.9.0",
        enable=enable,
        extra=extra or {},
    )
    for key, value in tags:
        ClusterTag.objects.create(instance=cluster, key=key, value=value)
    return cluster


class TestClusterTagSelector:
    def test_normalize_match_tags(self):
        selector = ClusterTagSelector({"match_tags": [" usage = ai_agent "]})
        assert selector.match_tags == {"usage=ai_agent"}

    @pytest.mark.parametrize(
        ("config", "message"),
        [
            (None, "cluster_selector must be an object"),
            ({"match_tags": "usage=ai_agent"}, "cluster_selector.match_tags must be a list"),
            ({"match_tags": [1]}, "cluster_selector.match_tags must contain key=value strings"),
            ({"match_tags": ["usage"]}, "cluster_selector tag must use key=value format"),
            ({"match_tags": ["=ai_agent"]}, "cluster_selector tag must use key=value format"),
            ({"match_tags": ["usage="]}, "cluster_selector tag must use key=value format"),
        ],
    )
    def test_invalid_config(self, config, message):
        with pytest.raises(ArgumentInvalidError, match=message):
            ClusterTagSelector(config)

    @pytest.mark.django_db
    def test_filter_clusters_by_all_match_tags(self):
        matched = create_db_cluster("ai-agent", tags=[("usage", "ai_agent"), ("region", "sz")])
        create_db_cluster("partial", tags=[("region", "sz")])
        create_db_cluster("untagged")

        selector = ClusterTagSelector({"match_tags": ["usage=ai_agent", "region=sz"]})
        assert selector.filter(ClusterModel.objects.all()) == [matched]


@pytest.mark.django_db
class TestProviderTaggedCluster:
    def test_selector_disabled_when_match_tags_empty(self):
        assert Provider().get_cluster_tag_selector() is None
        assert Provider(cluster_selector={"match_tags": []}).get_cluster_tag_selector() is None

    def test_select_enabled_cluster_with_tags(self):
        create_db_cluster("disabled", tags=[("usage", "ai_agent")], enable=False)
        matched = create_db_cluster("ai-agent", tags=[("usage", "ai_agent")])

        provider = Provider(cluster_selector={"match_tags": ["usage=ai_agent"]})
        assert provider.select_tagged_cluster(provider.get_cluster_tag_selector()) == matched

    def test_select_raises_when_no_cluster_matched(self):
        create_db_cluster("untagged")

        provider = Provider(cluster_selector={"match_tags": ["usage=ai_agent"]})
        with pytest.raises(OperationFailed, match="no available cluster matches tags"):
            provider.select_tagged_cluster(provider.get_cluster_tag_selector())

    def test_to_runtime_cluster_with_tls(self):
        db_cluster = create_db_cluster("tls", extra={"tls": {"ca": "ca-content"}})

        cluster = Provider.to_runtime_cluster(db_cluster)
        assert cluster.host == "tls.example.com"
        assert cluster.password == "secret"
        assert cluster.tls == {"ca": "ca-content"}

    def test_create_uses_tagged_cluster(self):
        matched = create_db_cluster("ai-agent", tags=[("usage", "ai_agent")])
        provider = Provider(cluster_selector={"match_tags": ["usage=ai_agent"]})

        with patch.object(Provider, "create_instance") as mocked_create:
            provider.create({"engine_app_name": "app"})

        _, _, context, cluster = mocked_create.call_args.args
        assert context["cluster_pk"] == matched.pk
        assert cluster.host == matched.host

    def test_delete_uses_cluster_recorded_in_bill(self):
        create_db_cluster("other", tags=[("usage", "ai_agent")])
        recorded = create_db_cluster("recorded", tags=[("usage", "ai_agent")])
        bill = InstanceBill.objects.create(name="app", action="create")
        bill.set_context({"cluster_pk": recorded.pk})
        bill.save()

        provider = Provider(cluster_selector={"match_tags": ["usage=ai_agent"]})
        instance_data = InstanceData(credentials={}, config={"bill": bill.uuid.hex})
        with patch.object(Provider, "delete_instance") as mocked_delete:
            provider.delete(instance_data)

        _, cluster, _ = mocked_delete.call_args.args
        assert cluster.host == recorded.host

    def test_delete_raises_when_cluster_missing(self):
        bill = InstanceBill.objects.create(name="app", action="create")

        provider = Provider(cluster_selector={"match_tags": ["usage=ai_agent"]})
        instance_data = InstanceData(credentials={}, config={"bill": bill.uuid.hex})
        with pytest.raises(OperationFailed, match="cluster of instance not found"):
            provider.delete(instance_data)
