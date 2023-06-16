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
"""Tests for region app"""
from typing import Dict, List

import pytest
from django.conf import settings
from django.core.management import call_command

from paas_wl.networking.egress.models import RegionClusterState
from paas_wl.resources.base.kres import KNode
from tests.paas_wl.utils.basic import random_resource_name

# GenState 依赖 k8s node 状态, 不能并发执行
pytestmark = [pytest.mark.django_db(databases=["default", "workloads"]), pytest.mark.xdist_group(name="k8s-node")]


REGION_NAME = settings.DEFAULT_REGION_NAME


class TestCommandGenState:
    @pytest.fixture
    def node_maker(self, k8s_client):
        created_node: List[str] = []

        def maker(body: Dict):
            node_name = body["metadata"]["name"]
            KNode(k8s_client).create_or_update(
                name=node_name,
                body=body,
            )
            created_node.append(node_name)

        yield maker
        for node_name in created_node:
            KNode(k8s_client).delete(name=node_name)

    @pytest.fixture
    def default_node_name(self):
        return "node-{}".format(random_resource_name())

    @pytest.fixture(autouse=True)
    def setup(self, request, node_maker, default_node_name):
        # Always create a new node before starting any tests
        node_maker(
            body={
                'metadata': {'name': default_node_name, 'labels': {'should_be_ignored': '1'}},
                'status': {"addresses": [{"address": "x.x.x.x", "type": "InternalIP"}]},
            }
        )
        yield

    def test_normal(self, default_node_name, k8s_client):
        call_command("region_gen_state", region=REGION_NAME, no_input=True, ignore_labels=["kind-node=true"])
        state = RegionClusterState.objects.filter(region=REGION_NAME).latest()

        assert state.nodes_cnt == 1
        assert state.nodes_name == [default_node_name]

        # Verify the labels field of kubernetes resources
        node_res = KNode(k8s_client).get(name=default_node_name)
        assert node_res.metadata.labels[state.name] == "1"

        # Call the command multiple times without any nodes updates should generates no new states
        call_command("region_gen_state", region=REGION_NAME, no_input=True, ignore_labels=["kind-node=true"])
        new_state = RegionClusterState.objects.filter(region=REGION_NAME).latest()
        assert new_state.id == state.id

    def test_with_adding_node(self, node_maker, default_node_name, k8s_client):
        call_command("region_gen_state", region=REGION_NAME, no_input=True, ignore_labels=["kind-node=true"])
        state = RegionClusterState.objects.filter(region=REGION_NAME).latest()

        # Create a new node
        node_name = "node-{}".format(random_resource_name())
        node_maker(body={"metadata": {"name": node_name}})

        call_command("region_gen_state", region=REGION_NAME, no_input=True, ignore_labels=["kind-node=true"])
        new_state = RegionClusterState.objects.filter(region=REGION_NAME).latest()

        assert new_state.id != state.id
        assert new_state.nodes_cnt - state.nodes_cnt == 1
        assert set(new_state.nodes_name) - set(state.nodes_name) == {node_name}

        # Verify the labels field of kubernetes resources
        node_res = KNode(k8s_client).get(name=default_node_name)
        assert node_res.metadata.labels[state.name] == "1"
        assert node_res.metadata.labels[new_state.name] == "1"

        # New node should only have the new state name in labels
        new_node_res = KNode(k8s_client).get(name=node_name)
        assert new_node_res.metadata.labels[state.name] is None
        assert new_node_res.metadata.labels[new_state.name] == "1"

    def test_ignore_labels(self):
        call_command(
            "region_gen_state",
            region=REGION_NAME,
            ignore_labels=["should_be_ignored=1", "another_label=some_value", "kind-node=true"],
            no_input=True,
        )
        state = RegionClusterState.objects.filter(region=REGION_NAME).latest()

        assert state.nodes_cnt == 0

    def test_ignore_multi_labels(self, node_maker):
        node_name = "node-{}".format(random_resource_name())
        node_maker(body={'metadata': {'name': node_name, 'labels': {'should_be_ignored_2': '1'}}})
        call_command(
            "region_gen_state",
            region=REGION_NAME,
            ignore_labels=["should_be_ignored=1", "should_be_ignored_2=1", "kind-node=true"],
            no_input=True,
        )
        state = RegionClusterState.objects.filter(region=REGION_NAME).latest()

        assert state.nodes_cnt == 0

    def test_ignore_masters(self, node_maker):
        node_name = "node-{}".format(random_resource_name())
        node_maker(
            body={
                'metadata': {
                    'name': node_name,
                    # Mark this node as a "master"
                    'labels': {'node-role.kubernetes.io/master': 'true'},
                },
            }
        )
        call_command("region_gen_state", region=REGION_NAME, no_input=True, ignore_labels=["kind-node=true"])
        state = RegionClusterState.objects.filter(region=REGION_NAME).latest()

        assert state.nodes_cnt == 1
