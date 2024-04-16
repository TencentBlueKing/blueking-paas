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
from unittest import mock

import pytest

from paas_wl.bk_app.mgrlegacy import DefaultAppProcessController
from paas_wl.bk_app.processes.kres_entities import Instance
from paas_wl.infras.resources.generation.mapper import get_mapper_proc_config_latest
from tests.paas_wl.bk_app.processes.test_controllers import make_process

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestDefaultAppProcessController:
    @pytest.fixture()
    def controller(self, wl_app):
        return DefaultAppProcessController.new_by_app(wl_app)

    def test_get_processes_info(self, controller, wl_app, mock_reader):
        mock_reader.set_processes([make_process(wl_app, "web"), make_process(wl_app, "worker")])
        mock_reader.set_instances(
            [
                Instance(app=wl_app, name="web-test", process_type="web"),
                Instance(app=wl_app, name="worker-test", process_type="worker"),
            ]
        )
        info = controller.get_processes_info()
        assert info.processes[0].type == "web"
        assert info.processes[1].type == "worker"
        assert info.processes[0].instances[0].name == "web-test"

    def test_scale_process(self, controller, wl_app):
        with mock.patch("paas_wl.infras.resources.base.kres.NameBasedOperations.patch") as kp, mock.patch(
            "paas_wl.workloads.networking.ingress.managers.service.service_kmodel"
        ) as ks:
            proc_config = get_mapper_proc_config_latest(wl_app, "worker")
            controller.scale(proc_config, 3)

            # Test service patch was performed
            assert ks.get.called
            assert not ks.create.called

            # Test deployment patch was performed
            assert kp.called
            args, kwargs = kp.call_args_list[0]
            assert kwargs.get("body")["spec"]["replicas"] == 3
