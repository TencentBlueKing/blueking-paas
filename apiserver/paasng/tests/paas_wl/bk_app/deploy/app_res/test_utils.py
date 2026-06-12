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

import pytest

from paas_wl.bk_app.deploy.app_res.utils import get_schedule_config
from paas_wl.infras.cluster.utils import get_cluster_by_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGetScheduleConfig:
    def test_basic(self, wl_app):
        """默认 only_cluster_default=False, node_selector 应包含 app config 的值"""

        config = wl_app.config_set.latest()
        config.node_selector = {"app": "test"}
        config.save()

        schedule = get_schedule_config(wl_app)
        assert schedule.node_selector == {"app": "test"}

    def test_skip_full_selector(self, wl_app):
        """only_cluster_default=True 时只用集群 default_node_selector"""

        cluster = get_cluster_by_app(wl_app)
        cluster.default_node_selector = {"cluster": "default"}
        cluster.save()

        config = wl_app.config_set.latest()
        config.node_selector = {"app": "test"}
        config.save()

        schedule = get_schedule_config(wl_app, only_cluster_default=True)
        assert schedule.node_selector == {"cluster": "default"}

    def test_tolerations_always_included(self, wl_app):
        """tolerations 不受 only_cluster_default 影响, 总是包含"""

        config = wl_app.config_set.latest()
        config.tolerations = [{"key": "app", "operator": "Equal", "value": "v", "effect": "NoExecute"}]
        config.save()

        assert get_schedule_config(wl_app).tolerations[0]["key"] == "app"
        assert get_schedule_config(wl_app, only_cluster_default=True).tolerations[0]["key"] == "app"
