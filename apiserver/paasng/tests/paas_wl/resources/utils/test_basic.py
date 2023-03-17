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
import pytest

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.resources.utils.basic import get_full_node_selector, get_full_tolerations, standardize_tolerations

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGetFullNodeSelector:
    def test_empty(self, wl_app):
        assert get_full_node_selector(wl_app) == {}

    def test_integrated(self, wl_app):
        config = wl_app.config_set.latest()
        config.node_selector = {'key1': 'value1', 'key-c': 'value-new'}
        config.save()

        cluster = get_cluster_by_app(wl_app)
        cluster.default_node_selector = {'key-c': 'value-c', 'key-c2': 'value-c2'}
        cluster.save()

        assert get_full_node_selector(wl_app) == {'key1': 'value1', 'key-c': 'value-new', 'key-c2': 'value-c2'}


class TestGetFullTolerations:
    def test_empty(self, wl_app):
        assert get_full_tolerations(wl_app) == []

    def test_integrated(self, wl_app):
        config = wl_app.config_set.latest()
        config.tolerations = [{'key': 'app', 'operator': 'Equal', 'value': 'value1', 'effect': 'NoExecute'}]
        config.save()

        cluster = get_cluster_by_app(wl_app)
        cluster.default_tolerations = [
            {'key': 'app-c', 'operator': 'Equal', 'value': 'value-c', 'effect': 'NoSchedule'}
        ]
        cluster.save()
        assert get_full_tolerations(wl_app) == [
            {'key': 'app', 'operator': 'Equal', 'value': 'value1', 'effect': 'NoExecute'},
            {'key': 'app-c', 'operator': 'Equal', 'value': 'value-c', 'effect': 'NoSchedule'},
        ]


class TestStandardizeTolerations:
    """Testcases for `TestTolerationDataHelper` class"""

    def test_condensed_list_valid(self):
        tolerations = [
            {'key': 'app', 'operator': 'Equal', 'value': 'value1', 'effect': 'NoExecute'},
            {'key': 'system-only', 'operator': 'Exists', 'effect': 'NoSchedule', 'foo': 'bar'},  # extra key
        ]
        assert standardize_tolerations(tolerations) == [
            {'key': 'app', 'operator': 'Equal', 'value': 'value1', 'effect': 'NoExecute'},
            {'key': 'system-only', 'operator': 'Exists', 'effect': 'NoSchedule'},
        ]
