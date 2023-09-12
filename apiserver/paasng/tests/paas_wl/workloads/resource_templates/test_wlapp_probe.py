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

from paas_wl.workloads.processes.models import WlAppProbe
from paas_wl.workloads.resource_templates.utils import AppProbeManager

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_app_probe_mgr(wl_app, process_type, check_mechanism_templates):
    WlAppProbe.objects.create(
        app=wl_app,
        process_type=process_type,
        probe_type='readiness',
        check_mechanism=check_mechanism_templates['readiness'],
    )
    WlAppProbe.objects.create(
        app=wl_app,
        process_type=process_type,
        probe_type='liveness',
        check_mechanism=check_mechanism_templates['liveness'],
    )

    app_probe_mgr = AppProbeManager(app=wl_app, process_type=process_type)
    readiness_probe = app_probe_mgr.get_readiness_probe()
    liveness_probe = app_probe_mgr.get_liveness_probe()

    assert readiness_probe
    assert readiness_probe.httpGet
    assert readiness_probe.httpGet.port == 8080
    assert readiness_probe.httpGet.path == "/healthz"
    assert liveness_probe
    assert liveness_probe.tcpSocket
    assert liveness_probe.tcpSocket.port == 60
