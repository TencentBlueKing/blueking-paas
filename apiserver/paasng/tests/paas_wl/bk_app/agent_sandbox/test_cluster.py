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

import pytest

from paas_wl.bk_app.agent_sandbox.cluster import find_available_port, list_available_hosts

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestFindAvailablePort:
    """Test find_available_port function."""

    def test_find_port_in_empty_set(self):
        """Test finding port when no ports are used."""
        port = find_available_port(30000, 30010, set())
        assert port is not None
        assert 30000 <= port <= 30010

    def test_find_port_with_some_used(self):
        """Test finding port when some ports are used."""
        used_ports = {30000, 30001, 30002}
        port = find_available_port(30000, 30010, used_ports)
        assert port is not None
        assert port not in used_ports
        assert 30000 <= port <= 30010

    def test_find_port_all_used(self):
        """Test that None is returned when all ports are used."""
        used_ports = set(range(30000, 30011))
        port = find_available_port(30000, 30010, used_ports)
        assert port is None


class TestListAvailableHosts:
    """Test list_available_hosts function."""

    def test_no_cluster_state(self):
        """Test that empty list is returned when no cluster state exists."""
        hosts = list_available_hosts("non-existent-cluster")
        assert hosts == []
