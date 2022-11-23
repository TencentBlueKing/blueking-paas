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
"""Tests for Kubernetes resources utils
"""
import time
from textwrap import dedent
from typing import Any, Dict
from unittest import mock

import pytest
import yaml
from kubernetes.client.rest import ApiException
from kubernetes.dynamic.resource import ResourceInstance
from urllib3.exceptions import RequestError

from paas_wl.resources.base.exceptions import CreateServiceAccountTimeout, ReadTargetStatusTimeout, ResourceMissing
from paas_wl.resources.base.kres import KDeployment, KNamespace, KPod, KServiceAccount, set_default_options
from tests.utils.basic import random_resource_name

pytestmark = pytest.mark.django_db


@pytest.fixture
def namespace_maker(k8s_client, k8s_version):
    def maker(ns):
        kres = KNamespace(k8s_client)
        obj, created = kres.get_or_create(ns)
        # k8s 1.8 只起了 apiserver 模拟测试, 不支持 wait_for_default_sa.
        # 其他更高版本的集群为集成测试, 必须执行 wait_for_default_sa, 否则测试可能会出错
        if (int(k8s_version.major), int(k8s_version.minor)) > (1, 8):
            kres.wait_for_default_sa(ns)
        return obj, created

    return maker


class TestNameBasedOps:
    def test_versions(self, k8s_client):
        assert isinstance(KNamespace(k8s_client).get_preferred_version(), str)
        assert isinstance(KNamespace(k8s_client).get_available_versions(), list)

    def test_delete(self, k8s_client):
        KNamespace(k8s_client).delete(random_resource_name())

    def test_delete_non_silent(self, k8s_client):
        with pytest.raises(ResourceMissing):
            KNamespace(k8s_client).delete(random_resource_name(), raise_if_non_exists=True)

    def test_delete_api_error(self, k8s_client):
        with pytest.raises(ApiException), mock.patch(
            "paas_wl.resources.base.kube_client.CoreDynamicClient.get_preferred_resource"
        ) as obj:
            obj().delete.side_effect = ApiException(status=400)
            KNamespace(k8s_client).delete(random_resource_name(), raise_if_non_exists=True)

    def test_get_or_create(self, k8s_client, namespace_maker):
        namespace = random_resource_name()
        obj, created = namespace_maker(namespace)
        assert obj.metadata.name == namespace
        assert created is True

        obj, created = namespace_maker(namespace)
        assert obj.metadata.name == namespace
        assert created is False

    def test_create_or_update(self, k8s_client, namespace_maker):
        namespace = random_resource_name()
        name = random_resource_name()
        deployment_body = construct_foo_deployment(name, KDeployment(k8s_client).get_preferred_version())

        obj, created = namespace_maker(namespace)
        assert obj.metadata.name == namespace
        assert created is True

        obj, created = KDeployment(k8s_client).create_or_update(name, namespace=namespace, body=deployment_body)
        assert obj.metadata.name == name
        assert obj.metadata.annotations["age"] == "3"
        assert created is True

        deployment_body['metadata']['annotations']["age"] = "4"
        obj, created = KDeployment(k8s_client).create_or_update(name, namespace=namespace, body=deployment_body)
        assert obj.metadata.name == name
        assert obj.metadata.annotations["age"] == "4"
        assert created is False

    def test_replace_or_patch(self, k8s_client, namespace_maker, resource_name):
        namespace = resource_name
        namespace_maker(namespace)

        deployment_body = construct_foo_deployment(resource_name, KDeployment(k8s_client).get_preferred_version())
        KDeployment(k8s_client).create_or_update(resource_name, namespace=namespace, body=deployment_body)

        deployment_body['metadata']['annotations']["age"] = "4"
        obj = KDeployment(k8s_client).replace_or_patch(resource_name, namespace=namespace, body=deployment_body)
        assert obj.metadata.annotations["age"] == "4"

    def test_patch(self, k8s_client, namespace_maker, resource_name):
        namespace = resource_name
        namespace_maker(namespace)

        deployment_body = construct_foo_deployment(resource_name, KDeployment(k8s_client).get_preferred_version())
        KDeployment(k8s_client).create_or_update(resource_name, namespace=namespace, body=deployment_body)

        # Only provide necessarily fields
        body = {'metadata': {'annotations': {"age": "4"}}}
        obj = KDeployment(k8s_client).patch(resource_name, namespace=namespace, body=body)
        assert obj.metadata.annotations["age"] == "4"


@pytest.mark.auto_create_ns
class TestLabelBasedOps:
    def test_create_watch_stream(self, k8s_client):
        namespace = "default"
        random_label = random_resource_name()

        pod_name = random_resource_name()
        # Create a pod to generate event
        KPod(k8s_client).create_or_update(
            pod_name, namespace=namespace, body=construct_foo_pod(pod_name, labels={"app": random_label})
        )
        stream = KPod(k8s_client).ops_label.create_watch_stream(
            {"app": random_label}, namespace=namespace, timeout_seconds=1, resource_version=0
        )
        # 在集成测试中, K8s 集群有可能会更新 Pod 的 metadata 和 status, 导致版本变化多次
        assert len(list(stream)) >= 1

    def test_filter_by_label(self, k8s_client):
        namespace = "default"
        random_label = random_resource_name()
        results = KPod(k8s_client).ops_label.list({"app": random_label}, namespace=namespace)
        assert len(results.items) == 0

        pod_name = random_resource_name()
        KPod(k8s_client).create_or_update(
            pod_name, namespace=namespace, body=construct_foo_pod(pod_name, labels={"app": random_label})
        )
        results = KPod(k8s_client).ops_label.list({"app": random_label}, namespace=namespace)
        assert len(results.items) == 1
        assert isinstance(results.items[0], ResourceInstance)

    def test_list_with_different_namespaces(self, k8s_client, namespace_maker):
        namespace = "default"
        another_namespace = random_resource_name()
        random_label = random_resource_name()
        results = KPod(k8s_client).ops_label.list({"app": random_label}, namespace=namespace)
        assert len(results.items) == 0

        obj, created = namespace_maker(another_namespace)
        assert obj.metadata.name == another_namespace
        assert created is True

        for i in range(2):
            pod_name = random_resource_name()
            KPod(k8s_client).create_or_update(
                pod_name, namespace=another_namespace, body=construct_foo_pod(pod_name, labels={"app": random_label})
            )
        results = KPod(k8s_client).ops_label.list({"app": random_label}, namespace=namespace)
        assert len(results.items) == 0

        results = KPod(k8s_client).ops_label.list({"app": random_label}, namespace=another_namespace)
        assert len(results.items) == 2

        results = KPod(k8s_client).ops_label.list({"app": "invalid-label-value"}, namespace=another_namespace)
        assert len(results.items) == 0

    def test_delete_collection(self, k8s_client):
        namespace = "default"
        random_label = random_resource_name()
        pod_name = random_resource_name()
        KPod(k8s_client).create_or_update(
            pod_name, namespace=namespace, body=construct_foo_pod(pod_name, labels={"app": random_label})
        )
        assert len(KPod(k8s_client).ops_label.list({"app": random_label}, namespace=namespace).items) == 1
        KPod(k8s_client).ops_label.delete_collection({"app": random_label}, namespace=namespace)
        assert len(KPod(k8s_client).ops_label.list({"app": random_label}, namespace=namespace).items) == 0

    def test_delete_individual(self, k8s_client):
        namespace = "default"
        random_label = random_resource_name()
        pod_name = random_resource_name()

        KPod(k8s_client).create_or_update(
            pod_name, namespace=namespace, body=construct_foo_pod(pod_name, labels={"app": random_label})
        )
        assert len(KPod(k8s_client).ops_label.list({"app": random_label}, namespace=namespace).items) == 1
        KPod(k8s_client).ops_label.delete_individual(
            {"app": random_label}, namespace=namespace, non_grace_period=False
        )
        assert len(KPod(k8s_client).ops_label.list({"app": random_label}, namespace=namespace).items) == 0


class TestDefaultOptions:
    @pytest.mark.skip
    def test_very_small_timeout(self, k8s_client):
        """Skip because the result if unstable"""
        namespace = "default"
        random_label = random_resource_name()
        set_default_options({"request_timeout": 0.00001})
        with pytest.raises(RequestError):
            KPod(k8s_client).ops_label.list({"app": random_label}, namespace=namespace)

        # Set the default timeout back to nothing
        set_default_options({"request_timeout": None})


class TestKNamespace:
    @pytest.mark.parametrize(
        'with_secrets, ret',
        [
            (True, True),
            # NOTE: 待确认: 在创建命名空间时, 会自动创建 SA, 需确认这个测试用例的场景.
            # (False, False),
        ],
    )
    def test_has_default_sa_with_or_without_secrets(self, k8s_client, with_secrets, ret, resource_name):
        namespace = resource_name
        assert KNamespace(k8s_client).default_sa_exists(namespace) is False
        KNamespace(k8s_client).get_or_create(namespace)

        # Create default SA
        sa_body: Dict[str, Any] = {
            'kind': 'ServiceAccount',
            'metadata': {'name': 'default'},
        }
        if with_secrets:
            sa_body['secrets'] = [{"name": "default-token-" + namespace}]

        KServiceAccount(k8s_client).create_or_update("default", body=sa_body, namespace=namespace)
        assert KNamespace(k8s_client).default_sa_exists(namespace) is ret

    def test_wait_for_default_sa_failed(self, k8s_client):
        time_started = time.time()
        namespace = random_resource_name()

        with pytest.raises(CreateServiceAccountTimeout):
            assert KNamespace(k8s_client).wait_for_default_sa(namespace, timeout=2)
        assert int(time.time() - time_started) == 2

    def test_wait_for_default_sa_succeed(self, k8s_client):
        namespace = random_resource_name()

        obj, created = KNamespace(k8s_client).get_or_create(namespace)
        assert obj.metadata.name == namespace
        assert created is True

        # Create default SA
        sa_body = {
            'kind': 'ServiceAccount',
            'metadata': {'name': 'default'},
            'secrets': [{"name": "default-token-" + namespace}],
        }
        KServiceAccount(k8s_client).create_or_update("default", body=sa_body, namespace=namespace)
        assert KNamespace(k8s_client).wait_for_default_sa(namespace, timeout=1) is None


class TestKPod:
    def test_wait_for_status_no_resource(self, k8s_client):
        time_started = time.time()
        name = random_resource_name()
        with pytest.raises(ReadTargetStatusTimeout):
            assert KPod(k8s_client).wait_for_status(
                name,
                ["Running"],
                namespace="default",
                timeout=0.2,
            )

        assert time.time() - time_started > 0.2

    def test_wait_for_status_normal(self, k8s_client, resource_name):
        KPod(k8s_client).create_or_update(resource_name, namespace="default", body=construct_foo_pod(resource_name))
        # Default status should be "Pending"
        assert (
            KPod(k8s_client).wait_for_status(
                resource_name,
                ["Pending"],
                namespace="default",
                timeout=0.2,
            )
            is None
        )

    def test_get_logs(self, k8s_client, resource_name):
        KPod(k8s_client).create_or_update(resource_name, namespace='default', body=construct_foo_pod(resource_name))
        logs = KPod(k8s_client).get_log(resource_name, namespace='default', timeout=0.1)
        assert logs is not None


#########
# Utils #
#########


def construct_foo_deployment(name: str, api_version: str = "extensions/v1beta1") -> Dict:
    manifest = yaml.load(
        dedent(
            '''\
        apiVersion: {api_version}
        kind: Deployment
        metadata:
            name: {name}
            annotations:
                age: "3"
        labels:
            app: nginx
        spec:
            replicas: 1
            selector:
                matchLabels:
                    deployment-name: {name}
            template:
                metadata:
                    labels:
                        deployment-name: {name}
                spec:
                    containers:
                    - name: main
                      image: busybox
    '''.format(
                api_version=api_version, name=name
            )
        )
    )
    return manifest


def construct_foo_pod(name: str, labels: Dict = {}) -> Dict:
    return {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {'name': name, 'labels': labels},
        'spec': {'containers': [{'name': "main", 'image': "busybox"}]},
    }
