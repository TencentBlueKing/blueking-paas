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
from django_dynamic_fixture import G

from paas_wl.monitoring.app_monitor.models import AppMetricsMonitor
from paas_wl.monitoring.app_monitor.utils import build_monitor_port

pytestmark = pytest.mark.django_db


def test_build_monitor_port(bk_stag_engine_app):
    assert build_monitor_port(bk_stag_engine_app) is None

    G(AppMetricsMonitor, port=5000, target_port=5001, app=bk_stag_engine_app)

    monitor_port = build_monitor_port(bk_stag_engine_app)
    assert monitor_port
    assert monitor_port.port == 5000
    assert monitor_port.target_port == 5001
    assert monitor_port.protocol == "TCP"
