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
from functools import partial

import pytest
from django_dynamic_fixture import G

from paas_wl.bk_app.deploy.processes import ProcSpecUpdater
from paas_wl.bk_app.processes.constants import ProcessTargetStatus
from paas_wl.bk_app.processes.models import ProcessSpec

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestProcSpecUpdater:
    @pytest.fixture
    def web_proc_factory(self, bk_stag_wl_app):
        return partial(G, ProcessSpec, engine_app=bk_stag_wl_app, name='web')

    def test_set_start(self, bk_stag_env, web_proc_factory):
        web_proc_factory(target_replicas=0, target_status=ProcessTargetStatus.STOP.value)

        updater = ProcSpecUpdater(bk_stag_env, 'web')
        assert updater.spec_object.target_status == ProcessTargetStatus.STOP.value

        updater.set_start()
        assert updater.spec_object.target_replicas == 1
        assert updater.spec_object.target_status == ProcessTargetStatus.START.value

    def test_set_stop(self, bk_stag_env, web_proc_factory):
        web_proc_factory(target_replicas=2, target_status=ProcessTargetStatus.START.value)

        updater = ProcSpecUpdater(bk_stag_env, 'web')
        updater.set_stop()
        assert updater.spec_object.target_replicas == 2
        assert updater.spec_object.target_status == ProcessTargetStatus.STOP.value

    def test_change_replicas_integrated(self, bk_stag_env, web_proc_factory):
        web_proc_factory(target_replicas=0, target_status=ProcessTargetStatus.STOP.value)

        updater = ProcSpecUpdater(bk_stag_env, 'web')
        updater.change_replicas(target_replicas=3)
        assert updater.spec_object.target_replicas == 3
        assert updater.spec_object.target_status == ProcessTargetStatus.START.value

        # Set the value to zero should stop the process
        updater.change_replicas(target_replicas=0)
        assert updater.spec_object.target_replicas == 0
        assert updater.spec_object.target_status == ProcessTargetStatus.STOP.value
