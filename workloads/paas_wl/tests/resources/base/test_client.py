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
from collections import namedtuple
from dataclasses import make_dataclass
from unittest.mock import Mock, patch

import pytest
from blue_krill.contextlib import nullcontext as does_not_raise
from django.conf import settings
from django.utils import timezone
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.release_controller.builder.infras import SlugBuilderTemplate
from paas_wl.release_controller.builder.procedures import generate_builder_name
from paas_wl.release_controller.entities import Runtime
from paas_wl.resources.base.client import K8sScheduler
from paas_wl.resources.base.controllers import BuildHandler
from paas_wl.resources.base.exceptions import (
    PodNotSucceededAbsentError,
    PodNotSucceededError,
    PodNotSucceededTimeoutError,
    ResourceDuplicate,
    ResourceMissing,
)
from paas_wl.resources.base.kres import KPod, PatchType
from paas_wl.resources.kube_res.base import Schedule
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.kubestatus import parse_pod
from paas_wl.workloads.processes.managers import AppProcessManager
from tests.conftest import CLUSTER_NAME_FOR_TESTING
from tests.utils.app import release_setup

from .test_kres import construct_foo_pod

pytestmark = pytest.mark.django_db

DummyObjectList = namedtuple('DummyObjectList', 'items metadata')

# Make a shortcut name
RG = settings.FOR_TESTS_DEFAULT_REGION


class TestClientProcess:
    @pytest.fixture
    def app(self, set_structure, bk_stag_engine_app):
        bk_stag_engine_app.region = RG
        bk_stag_engine_app.name = "bk-fake-stag"
        bk_stag_engine_app.save()
        set_structure(bk_stag_engine_app, {"web": 2, "worker": 1})
        return bk_stag_engine_app

    @pytest.fixture
    def release(self, app):
        release = release_setup(
            fake_app=app,
            build_params={"procfile": {"web": "python manage.py runserver", "worker": "python manage.py celery"}},
            release_params={"version": 5},
        )
        return release

    @pytest.fixture
    def scheduler_client(self):
        return K8sScheduler.from_cluster_name(CLUSTER_NAME_FOR_TESTING)

    @pytest.fixture
    def web_process(self, app, release):
        return AppProcessManager(app=app).assemble_process("web", release=release)

    @pytest.fixture
    def worker_process(self, app, release):
        return AppProcessManager(app=app).assemble_process("worker", release=release)

    @pytest.mark.mock_get_structured_app
    def test_deploy_processes(self, scheduler_client, web_process):
        with patch('paas_wl.resources.base.kres.NameBasedOperations.replace_or_patch') as kd, patch(
            'paas_wl.networking.ingress.managers.service.service_kmodel'
        ) as ks, patch('paas_wl.networking.ingress.managers.base.ingress_kmodel') as ki:
            ks.get.side_effect = AppEntityNotFound()
            ki.get.side_effect = AppEntityNotFound()

            scheduler_client.deploy_processes([web_process])

            # Check deployment resource
            assert kd.called
            deployment_args, deployment_kwargs = kd.call_args_list[0]
            assert deployment_kwargs.get('name') == f"{RG}-bk-fake-stag-web-python-deployment"
            assert deployment_kwargs.get('body')
            assert deployment_kwargs.get('namespace') == "bk-fake-stag"

            # Check service resource
            assert ks.get.called
            assert ks.create.called
            proc_service = ks.create.call_args_list[0][0][0]
            assert proc_service.name == f"{RG}-bk-fake-stag-web"

            # Check ingress resource
            assert ks.get.called
            assert ki.save.called
            proc_ingress = ki.save.call_args_list[0][0][0]
            assert proc_ingress.name == f"{RG}-bk-fake-stag"

    def test_scale_processes(self, scheduler_client, worker_process):
        with patch('paas_wl.resources.base.kres.NameBasedOperations.replace_or_patch') as kd, patch(
            'paas_wl.networking.ingress.managers.service.service_kmodel'
        ) as ks:
            worker_process.replicas = 3
            scheduler_client.scale_processes([worker_process])

            # Test service patch was performed
            assert ks.get.called
            assert not ks.create.called

            # Test deployment patch was performed
            assert kd.called
            args, kwargs = kd.call_args_list[0]
            assert kwargs.get('body')['spec']['replicas'] == 3
            assert kwargs.get('update_method') == 'patch'

    def test_shutdown_processes(self, scheduler_client, worker_process):
        DSpec = make_dataclass('Dspec', [('replicas', int)])
        DBody = make_dataclass('DBody', [('spec', DSpec)])
        kg = Mock(return_value=DBody(spec=DSpec(replicas=1)))
        with patch('paas_wl.resources.base.kres.NameBasedOperations.replace_or_patch') as kd, patch(
            'paas_wl.networking.ingress.managers.service.service_kmodel'
        ) as ks, patch('paas_wl.networking.ingress.managers.base.ingress_kmodel') as ki, patch(
            'paas_wl.resources.base.kres.NameBasedOperations.get', kg
        ):
            scheduler_client.shutdown_processes([worker_process])

            # 测试: 不删除 Service
            assert not ks.delete_by_name.called

            # 测试: 不删除 Ingress
            assert not ki.delete_by_name.called

            # Check deployment resource
            assert kd.called
            args, kwargs = kd.call_args_list[0]
            assert kwargs['body']['spec']['replicas'] == 0

    def test_shutdown_web_processes(self, scheduler_client, web_process):
        DSpec = make_dataclass('Dspec', [('replicas', int)])
        DBody = make_dataclass('DBody', [('spec', DSpec)])
        kg = Mock(return_value=DBody(spec=DSpec(replicas=1)))
        with patch('paas_wl.resources.base.kres.NameBasedOperations.replace_or_patch') as kd, patch(
            'paas_wl.networking.ingress.managers.service.service_kmodel'
        ) as ks, patch('paas_wl.networking.ingress.managers.base.ingress_kmodel') as ki, patch(
            'paas_wl.resources.base.kres.NameBasedOperations.get', kg
        ):
            # Make ingress point to web service
            faked_ingress = Mock()
            faked_ingress.configure_mock(service_name=f'{RG}-bk-fake-stag-web')
            ki.get.return_value = faked_ingress

            scheduler_client.shutdown_processes([web_process])

            # 测试: 不删除 Service
            assert not ks.delete_by_name.called

            # 测试: 不删除 Ingress
            assert not ki.delete_by_name.called

            # Check deployment resource
            assert kd.called
            args, kwargs = kd.call_args_list[0]
            assert kwargs['body']['spec']['replicas'] == 0


class TestClientBuild:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.scheduler_client = K8sScheduler.from_cluster_name(CLUSTER_NAME_FOR_TESTING)
        self.pod_template = SlugBuilderTemplate(
            name="slug-builder",
            namespace="bkapp-foo-stag",
            runtime=Runtime(image="blueking-fake.com:8090/bkpaas/slugrunner:latest", envs={"test": "1"}),
            schedule=Schedule(
                cluster_name="",
                node_selector={},
                tolerations=[{'key': 'region', 'operator': 'Equal', 'effect': 'NoExecute', 'value': 'sh'}],
            ),
        )

    def test_build_slug(self):
        namespace_create = Mock(return_value=None)
        namespace_check = Mock(return_value=True)

        pod_body = parse_pod(ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Completed"}}))
        kpod_get = Mock(return_value=pod_body)

        create_pod_body = parse_pod(
            ResourceInstance(None, {"kind": "Pod", "metadata": {"name": "bkapp-foo-stag-slug-pod"}})
        )
        kpod_create_or_update = Mock(return_value=(create_pod_body, True))

        with patch('paas_wl.resources.base.kres.NameBasedOperations.get_or_create', namespace_create), patch(
            'paas_wl.resources.base.kres.KNamespace.wait_for_default_sa', namespace_check
        ), patch('paas_wl.resources.base.kres.NameBasedOperations.get', kpod_get), patch(
            'paas_wl.resources.base.kres.NameBasedOperations.create_or_update', kpod_create_or_update
        ), patch(
            "paas_wl.resources.base.controllers.WaitPodDelete.wait"
        ):

            self.scheduler_client.build_slug(template=self.pod_template)
            assert kpod_get.called
            assert kpod_create_or_update.called

            args, kwargs = kpod_create_or_update.call_args_list[0]
            body = kwargs.get('body')
            assert body['metadata']['name'] == "slug-builder"
            assert body['spec']['containers'][0]['env'][0]['value'] == "1"
            assert len(body['spec']['tolerations']) == 1
            assert body['spec']['tolerations'][0]['key'] == 'region'
            assert body['spec']['tolerations'][0]['operator'] == 'Equal'

    def test_build_slug_exist(self):
        namespace_create = Mock(return_value=None)
        namespace_check = Mock(return_value=True)

        pod_body = ResourceInstance(
            None,
            {
                "kind": "Pod",
                "metadata": {"name": "foo"},
                "status": {"phase": "Running", "startTime": timezone.now().isoformat()},
            },
        )
        kpod_get = Mock(return_value=pod_body)

        with patch('paas_wl.resources.base.kres.NameBasedOperations.get_or_create', namespace_create), patch(
            'paas_wl.resources.base.kres.KNamespace.wait_for_default_sa', namespace_check
        ), patch('paas_wl.resources.base.kres.NameBasedOperations.get', kpod_get):

            with pytest.raises(ResourceDuplicate):
                self.scheduler_client.build_slug(template=self.pod_template)

    def test_delete_slug_pod(self):
        pod_body = ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Completed"}})
        kpod_get = Mock(return_value=pod_body)
        kpod_delete = Mock(return_value=None)

        with patch('paas_wl.resources.base.kres.NameBasedOperations.get', kpod_get), patch(
            'paas_wl.resources.base.kres.NameBasedOperations.delete', kpod_delete
        ):
            self.scheduler_client.delete_builder(namespace="bkapp-foo-stag", name="slug-builder")

            assert kpod_get.called
            assert kpod_delete.called
            args, kwargs = kpod_delete.call_args_list[0]
            assert args[0] == "slug-builder"
            assert kwargs.get('namespace') == "bkapp-foo-stag"

    def test_delete_slug_pod_missing(self):
        kpod_get = Mock(side_effect=ResourceMissing("bkapp-foo-stag-slug-pod", "bkapp-foo-stag"))
        kpod_delete = Mock(return_value=None)

        with patch('paas_wl.resources.base.kres.NameBasedOperations.get', kpod_get), patch(
            'paas_wl.resources.base.kres.NameBasedOperations.delete', kpod_delete
        ):
            self.scheduler_client.delete_builder(namespace="bkapp-foo-stag", name="bkapp-foo-stag")

            assert kpod_get.called
            assert not kpod_delete.called

    def test_delete_slug_pod_running(self):
        pod_body = ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Running"}})
        kpod_get = Mock(return_value=pod_body)
        kpod_delete = Mock(return_value=None)

        with patch('paas_wl.resources.base.kres.NameBasedOperations.get', kpod_get), patch(
            'paas_wl.resources.base.kres.NameBasedOperations.delete', kpod_delete
        ):
            self.scheduler_client.delete_builder(namespace="bkapp-foo-stag", name="bkapp-foo-stag")

            assert kpod_get.called
            assert not kpod_delete.called


@pytest.mark.auto_create_ns
class TestClientBuildNew:
    """New test cases using pytest"""

    def test_interrupt_builder(self, app, scheduler_client, k8s_client):
        builder_pod_name = BuildHandler.normalize_builder_name(generate_builder_name(app))
        KPod(k8s_client).create_or_update(
            builder_pod_name, namespace=app.namespace, body=construct_foo_pod(builder_pod_name)
        )

        assert scheduler_client.interrupt_builder(namespace=app.namespace, name=generate_builder_name(app)) is True

    def test_interrupt_builder_non_existent(self, app, scheduler_client):
        assert scheduler_client.interrupt_builder(namespace=app.namespace, name=generate_builder_name(app)) is False

    def test_wait_for_succeeded_no_pod(self, app, scheduler_client):
        with pytest.raises(PodNotSucceededAbsentError):
            scheduler_client.wait_build_succeeded(app.namespace, generate_builder_name(app), timeout=1)

    @pytest.mark.parametrize(
        'phase, exc_context',
        [
            ('Pending', pytest.raises(PodNotSucceededTimeoutError)),
            ('Running', pytest.raises(PodNotSucceededTimeoutError)),
            ('Failed', pytest.raises(PodNotSucceededError)),
            ('Unknown', pytest.raises(PodNotSucceededError)),
            ('Succeeded', does_not_raise()),
        ],
    )
    def test_wait_for_succeeded(self, phase, exc_context, app, scheduler_client, k8s_client):
        pod_name = BuildHandler.normalize_builder_name(generate_builder_name(app))
        body = construct_foo_pod(pod_name, restart_policy="Never")

        KPod(k8s_client).create_or_update(pod_name, namespace=app.namespace, body=body)

        body = {'status': {'phase': phase, 'conditions': []}}
        KPod(k8s_client).patch_subres('status', pod_name, namespace=app.namespace, body=body, ptype=PatchType.MERGE)

        with exc_context:
            scheduler_client.wait_build_succeeded(app.namespace, pod_name, timeout=1)
