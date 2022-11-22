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
from contextlib import contextmanager

import pytest
from django.conf import settings
from django.core.management import call_command

from paas_wl.cluster.utils import get_default_cluster_by_region
from paas_wl.networking.egress.models import RCStateAppBinding
from paas_wl.resources.base.kres import KNode
from paas_wl.resources.utils.app import get_scheduler_client
from paas_wl.resources.utils.basic import get_full_node_selector
from tests.utils.basic import random_resource_name

pytestmark = pytest.mark.django_db


class TestRegionAPIs:
    @pytest.fixture
    def url_default(self, fake_app):
        return f'/regions/{fake_app.region}/apps/{fake_app.name}/rcstate_binding/'

    @contextmanager
    def add_node_to_cluster(self, region):
        # Create a RegionClusterState object first
        sched_client = get_scheduler_client(get_default_cluster_by_region(region).name)
        kube_client = sched_client.client
        node_name = "node-{}".format(random_resource_name())
        KNode(kube_client).create_or_update(
            node_name,
            body={
                'metadata': {'name': node_name},
                'status': {"addresses": [{"address": "x.x.x.x", "type": "InternalIP"}]},
            },
        )
        try:
            yield
        finally:
            # Always destroy all nodes when exiting
            KNode(kube_client).ops_label.delete_collection({})

    def test_create_normal(self, api_client, url_default, fake_app):
        region = settings.FOR_TESTS_DEFAULT_REGION
        with self.add_node_to_cluster(region):
            call_command("region_gen_state", region=region, no_input=True)

            resp = api_client.post(url_default)
            assert resp.status_code == 201
            assert any(
                node_ip["internal_ip_address"] == "x.x.x.x" for node_ip in resp.json()["state"]["node_ip_addresses"]
            )

            # Verify node_selector
            node_selector = get_full_node_selector(fake_app)
            assert node_selector[resp.json()["state"]["name"]] == '1'

    def test_create_duplicated(self, api_client, url_default):
        region = settings.FOR_TESTS_DEFAULT_REGION
        with self.add_node_to_cluster(region):
            call_command("region_gen_state", region=region, no_input=True)

            api_client.post(url_default)
            # Duplicated POST
            resp = api_client.post(url_default)

            assert resp.status_code == 400
            assert resp.json()["code"] == "CREATE_RCSTATE_BINDING_ERROR"

    def test_integrated(self, api_client, url_default, fake_app):
        # Test integrated APIs
        region = settings.FOR_TESTS_DEFAULT_REGION
        assert RCStateAppBinding.objects.filter(app=fake_app).count() == 0

        with self.add_node_to_cluster(region):
            call_command("region_gen_state", region=region, no_input=True)

            api_client.post(url_default).json()
            binding = RCStateAppBinding.objects.get(app=fake_app)
            state_name = binding.state.name
            assert binding.state.nodes_data != []

            # Delete the binding
            resp = api_client.delete(url_default)
            assert resp.status_code == 204

            assert RCStateAppBinding.objects.filter(app=fake_app).count() == 0

            # Verify node_selector
            node_selector = get_full_node_selector(fake_app)
            assert node_selector.get(state_name) is None
