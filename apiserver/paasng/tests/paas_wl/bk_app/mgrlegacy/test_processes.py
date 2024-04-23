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

from paas_wl.bk_app.mgrlegacy.processes import get_processes_info
from paas_wl.bk_app.processes.kres_entities import Instance
from tests.paas_wl.bk_app.processes.test_controllers import make_process

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_get_processes_info(wl_app, mock_reader):
    mock_reader.set_processes([make_process(wl_app, "web"), make_process(wl_app, "worker")])
    mock_reader.set_instances(
        [
            Instance(app=wl_app, name="web-test", process_type="web"),
            Instance(app=wl_app, name="worker-test", process_type="worker"),
        ]
    )
    info = get_processes_info(wl_app)
    assert info.processes[0].type == "web"
    assert info.processes[1].type == "worker"
    assert info.processes[0].instances[0].name == "web-test"
