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
from django_dynamic_fixture import G

from paasng.platform.bkapp_model.entities import Metric, Monitoring, Observability
from paasng.platform.bkapp_model.entities_syncer import sync_observability
from paasng.platform.bkapp_model.models import ObservabilityConfig

pytestmark = pytest.mark.django_db(databases=["default"])


class Test__sync_observability:
    def test_create(self, bk_module):
        metric = {"process": "web", "service_name": "metric", "path": "/metrics", "params": {"foo": "bar"}}
        ret = sync_observability(
            module=bk_module,
            observability=Observability(monitoring={"metrics": [metric]}),
        )
        assert ret.created_num == 1
        assert ret.updated_num == 0
        assert ret.deleted_num == 0

        assert ObservabilityConfig.objects.get(module=bk_module).monitoring.metrics == [Metric(**metric)]

    def test_update(self, bk_module):
        metric = {"process": "web", "service_name": "metric", "path": "/metrics", "params": {"foo": "bar"}}
        G(ObservabilityConfig, module=bk_module, monitoring=Monitoring(metrics=[metric]))

        new_metric = {
            "process": "celery",
            "service_name": "metric",
            "path": "/celery/metrics",
            "params": {"foo": "bar"},
        }

        ret = sync_observability(
            module=bk_module,
            observability=Observability(monitoring={"metrics": [new_metric]}),
        )

        assert ret.created_num == 0
        assert ret.updated_num == 1
        assert ret.deleted_num == 0

        obj = ObservabilityConfig.objects.get(module=bk_module)
        assert obj.monitoring.metrics == [Metric(**new_metric)]
        assert obj.last_monitoring.metrics == [Metric(**metric)]
        assert obj.last_metric_processes == ["web"]
        assert obj.metric_processes == ["celery"]
