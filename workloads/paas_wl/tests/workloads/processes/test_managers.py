# -*- coding: utf-8 -*-
from unittest import mock

import pytest
from django.conf import settings

from paas_wl.resources.base.generation import get_mapper_version
from paas_wl.resources.base.kres import KPod
from paas_wl.resources.kube_res.base import AppEntityManager
from paas_wl.resources.utils.basic import get_client_by_app
from paas_wl.workloads.processes.models import Process
from paas_wl.workloads.processes.readers import instance_kmodel, process_kmodel
from paas_wl.workloads.processes.serializers import extract_type_from_name
from tests.utils.app import release_setup

pytestmark = [pytest.mark.django_db, pytest.mark.ensure_k8s_namespace]


@pytest.fixture
def client(app):
    return get_client_by_app(app)


@pytest.fixture
def release(app, set_structure):
    set_structure(app, {"web": 2})
    return release_setup(
        fake_app=app,
        build_params={"procfile": {"web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"}},
        release_params={"version": 2},
    )


@pytest.fixture
def process(release):
    return Process.from_release(type_="web", release=release)


@pytest.fixture
def process_manager():
    return AppEntityManager(Process)


@pytest.fixture()
def v1_mapper(process):
    return get_mapper_version(target="v1")


class TestProcInstManager:
    """TestCases for ProcInst"""

    @pytest.fixture
    def pod(self, app, release, client, process_manager, process, v1_mapper):
        pod_name = v1_mapper.pod(process=process).name
        serializer = process_manager._make_serializer(app)
        pod_body = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {'labels': v1_mapper.pod(process=process).labels, 'name': pod_name},
            'spec': serializer._construct_pod_body_specs(process),  # type: ignore
        }
        pod, _ = KPod(client).create_or_update(name=pod_name, namespace=process.app.namespace, body=pod_body)
        return pod

    def test_query_instances(self, app, pod):
        # Query process instances
        insts = instance_kmodel.list_by_process_type(app, 'web')
        assert len(insts) == 1
        assert insts[0].process_type == 'web'
        assert insts[0].envs

    def test_query_instances_without_process_id_label(self, client, app, pod):
        # 使用 kind 部署的 k8s 集群会导致 Pod 的内容被更新, 因此需要获取最新的 Pod
        current_pod = KPod(client).get(name=pod.metadata.name, namespace=pod.metadata.namespace)

        # Delete `process_id` label to simulate resources created by legacy engine versions
        del current_pod.metadata.labels.__dict__['process_id']
        KPod(client).replace_or_patch(name=pod.metadata.name, body=current_pod, namespace=pod.metadata.namespace)

        # Query process instances
        insts = instance_kmodel.list_by_process_type(app, 'web')
        assert len(insts) == 1

    def test_watch_from_rv0(self, client, app, pod):
        # 使用 kind 部署的 k8s 集群会导致 Pod 的内容被更新, 因此需要获取最新的 Pod
        current_pod = KPod(client).get(name=pod.metadata.name, namespace=pod.metadata.namespace)

        current_pod.metadata.labels.foo = 'bar'
        KPod(client).replace_or_patch(name=pod.metadata.name, body=current_pod, namespace=pod.metadata.namespace)

        events = list(instance_kmodel.watch_by_app(app, resource_version=0, timeout_seconds=1))
        assert len(events) > 0

    def test_watch_from_empty_rv(self, app, pod):
        inst = instance_kmodel.list_by_process_type(app, 'web')[0]
        events = list(
            instance_kmodel.watch_by_app(app, resource_version=inst.get_resource_version(), timeout_seconds=1)
        )
        assert len(events) == 0

        events = list(instance_kmodel.watch_by_app(app, resource_version=0, timeout_seconds=1))
        assert len(events) > 0

    def test_get_logs(self, app, pod):
        # Query process instances
        inst = instance_kmodel.list_by_process_type(app, 'web')[0]
        with mock.patch('paas_wl.workloads.processes.models.Instance.Meta.kres_class') as kp:
            instance_kmodel.get_logs(inst)
            assert kp().get_log.called

    def test_list_with_meta(self, app, pod):
        resources = instance_kmodel.list_by_app_with_meta(app)

        assert resources.metadata is not None
        rv = resources.get_resource_version()
        assert isinstance(rv, str)
        assert rv != ''


class TestProcSpecsManager:
    """TestCases for ProcSpecs"""

    @pytest.fixture
    def process(self, app, release, process_manager, process, v1_mapper):
        process_manager.create(process, mapper_version=v1_mapper)
        return process

    def test_query_instances(self, process):
        # Query ProcSpecs objects
        objs = process_kmodel.list_by_app(process.app)
        assert len(objs) == 1
        assert objs[0].type == 'web'
        assert objs[0].replicas == 2

        obj = process_kmodel.get_by_type(process.app, 'web')
        # 集成测试中的 k8s 集群会修改 metadata
        obj.metadata = {}
        objs[0].metadata = {}
        assert obj == objs[0]

    def test_watch_from_rv0(self, process):
        events = list(process_kmodel.watch_by_app(process.app, resource_version=0, timeout_seconds=1))
        assert len(events) > 0
        event = events[0]
        assert event['type'] == 'ADDED'
        assert event['res_object'].type == 'web'


class TestExtractTypeFromName:
    @pytest.mark.parametrize(
        'name,namespace,proc_type',
        [
            (
                f'{settings.FOR_TESTS_DEFAULT_REGION}-bkapp-foo-prod-web-gunicorn-deployment',
                'bkapp-foo-prod',
                'web',
            ),
            (
                f'{settings.FOR_TESTS_DEFAULT_REGION}-bkapp-foo-prod-web-gunicorn-deployment-858bf9c468-rms24',
                'bkapp-foo-prod',
                'web',
            ),
            ('invalid_name', 'xxx', None),
        ],
    )
    def test_main(self, name, namespace, proc_type):
        assert extract_type_from_name(name, namespace) == proc_type
