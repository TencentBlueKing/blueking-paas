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
from textwrap import dedent

import pytest
from django_dynamic_fixture import G

from paas_wl.release_controller.hooks.entities import Command, command_kmodel
from paas_wl.release_controller.hooks.models import Command as CommandModel
from paas_wl.resources.base.controllers import CommandHandler
from paas_wl.resources.base.exceptions import PodTimeoutError
from paas_wl.resources.base.generation import get_mapper_version
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.resource_templates.constants import AppAddOnType
from paas_wl.workloads.resource_templates.models import AppAddOnTemplate

pytestmark = pytest.mark.django_db(databases=["workloads"])


@pytest.mark.auto_create_ns
class TestCommand:
    @pytest.fixture(autouse=True)
    def skip_if(self, k8s_version):
        # 测试用例需要真实的 k8s 集群
        if (int(k8s_version.major), int(k8s_version.minor)) <= (1, 8):
            pytest.skip("dummy cluster can't run e2e test")

    @pytest.fixture
    def command_model(self, wl_app):
        config = wl_app.latest_config
        config.runtime.image = "busybox:latest"
        config.runtime.endpoint = ["sh", "-c"]
        config.save()
        return G(
            CommandModel,
            app=wl_app,
            command=r"echo\ 'finished'",
            config=config,
        )

    @pytest.fixture
    def command(self, command_model):
        return Command.from_db_obj(command_model)

    @pytest.fixture
    def handler(self, k8s_client, settings):
        return CommandHandler(
            client=k8s_client,
            default_connect_timeout=settings.K8S_DEFAULT_CONNECT_TIMEOUT,
            default_request_timeout=settings.K8S_DEFAULT_CONNECT_TIMEOUT + settings.K8S_DEFAULT_READ_TIMEOUT,
            mapper_version=get_mapper_version(
                target=settings.GLOBAL_DEFAULT_MAPPER_VERSION, init_kwargs={'client': k8s_client}
            ),
        )

    def test_run(self, handler, command):
        with pytest.raises(AppEntityNotFound):
            command_kmodel.get(command.app, command.name)

        handler.run_command(command)
        handler._wait_pod_succeeded(namespace=command.app.namespace, pod_name=command.name, timeout=60)
        assert handler.get_command_logs(command, timeout=60).read() == b"finished\n"
        command_in_k8s = command_kmodel.get(command.app, command.name)
        assert command_in_k8s.phase == "Succeeded"

    @pytest.fixture
    def sidecar(self, wl_app):
        template = G(
            AppAddOnTemplate,
            name="sidecar",
            spec=dedent(
                """
                {
                    "name": "sidecar",
                    "image": "busybox:latest",
                    "command": ["sleep", "600"]
                }
            """
            ),
            type=AppAddOnType.SIMPLE_SIDECAR,
        )
        return template.link_to_app(wl_app)

    def test_run_with_sidecar(self, handler, command, sidecar):
        handler.run_command(command)
        handler.wait_for_succeeded(command, timeout=60)
        assert handler.get_command_logs(command, timeout=60).read() == b"finished\n"
        with pytest.raises(PodTimeoutError):
            handler._wait_pod_succeeded(namespace=command.app.namespace, pod_name=command.name, timeout=1)
        command_in_k8s = command_kmodel.get(command.app, command.name)
        # 虽然 Pod 仍在运行, 但是主容器已退出
        assert command_in_k8s.phase == "Running"
        assert command_in_k8s.main_container_exit_code == 0

    def test_delete_with_sidecar(self, handler, command, sidecar):
        handler.run_command(command)
        handler.wait_for_succeeded(command, timeout=60)

        command_in_k8s = command_kmodel.get(command.app, command.name)
        assert command_in_k8s.phase == "Running"

        waitable = handler.delete_command(command)
        assert waitable is not None
        waitable.wait(60)
        with pytest.raises(AppEntityNotFound):
            command_kmodel.get(command.app, command.name)
