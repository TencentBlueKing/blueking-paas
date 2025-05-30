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

from dataclasses import make_dataclass
from textwrap import dedent
from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paas_wl.bk_app.applications.entities import BuildArtifactMetadata
from paas_wl.bk_app.deploy.app_res.controllers import CommandHandler, ProcessesHandler
from paas_wl.bk_app.processes.managers import AppProcessManager
from paas_wl.infras.resource_templates.constants import AppAddOnType
from paas_wl.infras.resource_templates.models import AppAddOnTemplate
from paas_wl.infras.resources.base.exceptions import PodTimeoutError
from paas_wl.infras.resources.generation.mapper import get_mapper_proc_config_latest
from paas_wl.infras.resources.generation.version import AppResVerManager
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.release_controller.constants import ImagePullPolicy
from paas_wl.workloads.release_controller.hooks.kres_entities import Command, command_kmodel
from paas_wl.workloads.release_controller.hooks.models import Command as CommandModel

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

region = settings.DEFAULT_REGION_NAME


@pytest.mark.auto_create_ns()
class TestCommand:
    @pytest.fixture(autouse=True)
    def _skip_if(self, k8s_version):
        # 测试用例需要真实的 k8s 集群
        if (int(k8s_version.major), int(k8s_version.minor)) <= (1, 8):
            pytest.skip("dummy cluster can't run e2e test")

    @pytest.fixture()
    def command_model(self, wl_app, wl_build):
        wl_build.image = "busybox:latest"
        wl_build.artifact_metadata = BuildArtifactMetadata(entrypoint=["sh", "-c"])
        wl_build.save()
        config = wl_app.latest_config
        config.runtime.image_pull_policy = ImagePullPolicy.NEVER
        config.save()
        return G(
            CommandModel,
            app=wl_app,
            command=r"echo\ 'finished'",
            config=config,
            build=wl_build,
        )

    @pytest.fixture()
    def command(self, command_model):
        return Command.from_db_obj(command_model)

    @pytest.fixture()
    def handler(self, k8s_client, settings):
        return CommandHandler(client=k8s_client)

    def test_run(self, handler, command):
        with pytest.raises(AppEntityNotFound):
            command_kmodel.get(command.app, command.name)

        handler.run_command(command)
        handler._wait_pod_succeeded(namespace=command.app.namespace, pod_name=command.name, timeout=60)
        assert handler.get_command_logs(command, timeout=60).read() == b"finished\n"
        command_in_k8s = command_kmodel.get(command.app, command.name)
        assert command_in_k8s.phase == "Succeeded"

    @pytest.fixture()
    def sidecar(self, wl_app):
        template = G(
            AppAddOnTemplate,
            name="sidecar",
            spec=dedent(
                """
                {
                    "name": "sidecar",
                    "image": "busybox:latest",
                    "command": ["sleep", "600"],
                    "imagePullPolicy": "Never"
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


class TestProcessHandler:
    @pytest.fixture(autouse=True)
    def _set_res_version(self, wl_app, wl_release):
        AppResVerManager(wl_app).update("v1")

    @pytest.fixture()
    def web_process(self, wl_app, wl_release):
        return AppProcessManager(app=wl_app).assemble_process("web", release=wl_release)

    @pytest.fixture()
    def worker_process(self, wl_app, wl_release):
        return AppProcessManager(app=wl_app).assemble_process("worker", release=wl_release)

    @pytest.mark.mock_get_structured_app()
    def test_deploy_processes(self, wl_app, web_process):
        handler = ProcessesHandler.new_by_app(wl_app)
        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.replace_or_patch") as kd,
            patch("paas_wl.workloads.networking.ingress.managers.service.service_kmodel") as ks,
            patch("paas_wl.workloads.networking.ingress.managers.base.ingress_kmodel") as ki,
        ):
            ks.get.side_effect = AppEntityNotFound()
            ki.get.side_effect = AppEntityNotFound()

            handler.deploy([web_process])

            # Check deployment resource
            assert kd.called
            deployment_args, deployment_kwargs = kd.call_args_list[0]
            assert deployment_kwargs.get("name") == f"{region}-{wl_app.name}-web-python-deployment"
            assert deployment_kwargs.get("body")
            assert deployment_kwargs.get("namespace") == wl_app.namespace

            # Check service resource
            assert ks.get.called
            assert ks.create.called
            proc_service = ks.create.call_args_list[0][0][0]
            assert proc_service.name == f"{region}-{wl_app.name}-web"

            # Check ingress resource
            assert ks.get.called
            assert ki.save.called
            proc_ingress = ki.save.call_args_list[0][0][0]
            assert proc_ingress.name == f"{region}-{wl_app.name}"

    def test_scale_process(self, wl_app):
        handler = ProcessesHandler.new_by_app(wl_app)
        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.patch") as kp,
            patch("paas_wl.workloads.networking.ingress.managers.service.service_kmodel") as ks,
        ):
            proc_config = get_mapper_proc_config_latest(wl_app, "worker")
            handler.scale(proc_config, 3)

            # Test service patch was performed
            assert ks.get.called
            assert not ks.create.called

            # Test deployment patch was performed
            assert kp.called
            args, kwargs = kp.call_args_list[0]
            assert kwargs.get("body")["spec"]["replicas"] == 3

    def test_shutdown_process(self, wl_app):
        handler = ProcessesHandler.new_by_app(wl_app)
        d_spec = make_dataclass("Dspec", [("replicas", int)])
        d_body = make_dataclass("DBody", [("spec", d_spec)])
        kg = Mock(return_value=d_body(spec=d_spec(replicas=1)))

        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.patch") as kp,
            patch("paas_wl.workloads.networking.ingress.managers.service.service_kmodel") as ks,
            patch("paas_wl.workloads.networking.ingress.managers.base.ingress_kmodel") as ki,
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kg),
        ):
            proc_config = get_mapper_proc_config_latest(wl_app, "worker")
            handler.shutdown(proc_config)

            # 测试: 不删除 Service
            assert not ks.delete_by_name.called

            # 测试: 不删除 Ingress
            assert not ki.delete_by_name.called

            # Check deployment resource
            assert kp.called
            args, kwargs = kp.call_args_list[0]
            assert kwargs["body"]["spec"]["replicas"] == 0

    def test_shutdown_web_processes(self, wl_app, web_process):
        handler = ProcessesHandler.new_by_app(wl_app)
        d_spec = make_dataclass("Dspec", [("replicas", int)])
        d_body = make_dataclass("DBody", [("spec", d_spec)])
        kg = Mock(return_value=d_body(spec=d_spec(replicas=1)))

        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.patch") as kp,
            patch("paas_wl.workloads.networking.ingress.managers.service.service_kmodel") as ks,
            patch("paas_wl.workloads.networking.ingress.managers.base.ingress_kmodel") as ki,
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kg),
        ):
            # Make ingress point to web service
            faked_ingress = Mock()
            faked_ingress.configure_mock(service_name=f"{region}-{wl_app.name}-web")
            ki.get.return_value = faked_ingress

            proc_config = get_mapper_proc_config_latest(wl_app, "worker")
            handler.shutdown(proc_config)

            # 测试: 不删除 Service
            assert not ks.delete_by_name.called

            # 测试: 不删除 Ingress
            assert not ki.delete_by_name.called

            # Check deployment resource
            assert kp.called
            args, kwargs = kp.call_args_list[0]
            assert kwargs["body"]["spec"]["replicas"] == 0
