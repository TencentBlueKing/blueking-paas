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

"""Tests for Kubernetes resources utils"""

import math
import time
from textwrap import dedent
from typing import Any, Dict, Optional
from unittest import mock

import pytest
import yaml
from kubernetes.client.rest import ApiException
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.infras.resources.base.constants import KUBECTL_RESTART_RESOURCE_KEY
from paas_wl.infras.resources.base.exceptions import (
    CreateServiceAccountTimeout,
    ReadTargetStatusTimeout,
    ResourceMissing,
)
from paas_wl.infras.resources.base.kres import BatchOperations, KDeployment, KNamespace, KPod, KServiceAccount
from tests.paas_wl.utils.basic import random_resource_name

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


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
        with mock.patch("paas_wl.infras.resources.base.kube_client.CoreDynamicClient.get_preferred_resource") as obj:
            obj().delete.side_effect = ApiException(status=400)
            with pytest.raises(ApiException):
                KNamespace(k8s_client).delete(random_resource_name(), raise_if_non_exists=True)

    def test_get_or_create(self, k8s_client, namespace_maker):
        namespace = random_resource_name()
        obj, created = namespace_maker.make(namespace)
        assert obj.metadata.name == namespace
        assert created is True

        obj, created = namespace_maker.make(namespace)
        assert obj.metadata.name == namespace
        assert created is False

    def test_create_or_update(self, k8s_client, namespace_maker):
        namespace = random_resource_name()
        name = random_resource_name()
        deployment_body = construct_foo_deployment(name, KDeployment(k8s_client).get_preferred_version())

        obj, created = namespace_maker.make(namespace)
        assert obj.metadata.name == namespace
        assert created is True

        obj, created = KDeployment(k8s_client).create_or_update(name, namespace=namespace, body=deployment_body)
        assert obj.metadata.name == name
        assert obj.metadata.annotations["age"] == "3"
        assert created is True

        deployment_body["metadata"]["annotations"]["age"] = "4"
        obj, created = KDeployment(k8s_client).create_or_update(name, namespace=namespace, body=deployment_body)
        assert obj.metadata.name == name
        assert obj.metadata.annotations["age"] == "4"
        assert created is False

    def test_replace_or_patch(self, k8s_client, namespace_maker, resource_name):
        namespace = resource_name
        namespace_maker.make(namespace)

        deployment_body = construct_foo_deployment(resource_name, KDeployment(k8s_client).get_preferred_version())
        KDeployment(k8s_client).create_or_update(resource_name, namespace=namespace, body=deployment_body)

        deployment_body["metadata"]["annotations"]["age"] = "4"
        obj = KDeployment(k8s_client).replace_or_patch(resource_name, namespace=namespace, body=deployment_body)
        assert obj.metadata.annotations["age"] == "4"

    def test_patch(self, k8s_client, namespace_maker, resource_name):
        namespace = resource_name
        namespace_maker.make(namespace)

        deployment_body = construct_foo_deployment(resource_name, KDeployment(k8s_client).get_preferred_version())
        KDeployment(k8s_client).create_or_update(resource_name, namespace=namespace, body=deployment_body)

        # Only provide necessarily fields
        body = {"metadata": {"annotations": {"age": "4"}}}
        obj = KDeployment(k8s_client).patch(resource_name, namespace=namespace, body=body)
        assert obj.metadata.annotations["age"] == "4"


@pytest.mark.auto_create_ns
class TestBatchOps:
    def test_create_watch_stream(self, k8s_client, wl_app):
        # Create a pod to generate event
        KPod(k8s_client).create_or_update(
            wl_app.scheduler_safe_name,
            namespace=wl_app.namespace,
            body=construct_foo_pod(wl_app.scheduler_safe_name, labels={"app": wl_app.name}),
        )
        stream = KPod(k8s_client).ops_batch.create_watch_stream(
            {"app": wl_app.name}, namespace=wl_app.namespace, timeout_seconds=1, resource_version=0
        )
        # 在集成测试中, K8s 集群有可能会更新 Pod 的 metadata 和 status, 导致版本变化多次
        assert len(list(stream)) >= 1

    def test_filter_by_labels(self, k8s_client, wl_app):
        results = KPod(k8s_client).ops_batch.list({"app": wl_app.name}, namespace=wl_app.namespace)
        assert len(results.items) == 0

        KPod(k8s_client).create_or_update(
            wl_app.scheduler_safe_name,
            namespace=wl_app.namespace,
            body=construct_foo_pod(wl_app.scheduler_safe_name, labels={"app": wl_app.name}),
        )
        results = KPod(k8s_client).ops_batch.list({"app": wl_app.name}, namespace=wl_app.namespace)
        assert len(results.items) == 1
        assert isinstance(results.items[0], ResourceInstance)

    def test_list_with_different_namespaces(self, k8s_client, namespace_maker, wl_app):
        another_namespace = random_resource_name()
        results = KPod(k8s_client).ops_batch.list({"app": wl_app.name}, namespace=wl_app.namespace)
        assert len(results.items) == 0

        obj, created = namespace_maker.make(another_namespace)
        assert obj.metadata.name == another_namespace
        assert created is True

        for _ in range(2):
            pod_name = random_resource_name()
            KPod(k8s_client).create_or_update(
                pod_name, namespace=another_namespace, body=construct_foo_pod(pod_name, labels={"app": wl_app.name})
            )
        results = KPod(k8s_client).ops_batch.list({"app": wl_app.name}, namespace=wl_app.namespace)
        assert len(results.items) == 0

        results = KPod(k8s_client).ops_batch.list({"app": wl_app.name}, namespace=another_namespace)
        assert len(results.items) == 2

        results = KPod(k8s_client).ops_batch.list({"app": "invalid-label-value"}, namespace=another_namespace)
        assert len(results.items) == 0

    def test_delete_collection(self, k8s_client, wl_app):
        KPod(k8s_client).create_or_update(
            wl_app.scheduler_safe_name,
            namespace=wl_app.namespace,
            body=construct_foo_pod(wl_app.scheduler_safe_name, labels={"app": wl_app.name}),
        )
        assert len(KPod(k8s_client).ops_batch.list({"app": wl_app.name}, namespace=wl_app.namespace).items) == 1
        KPod(k8s_client).ops_batch.delete_collection({"app": wl_app.name}, namespace=wl_app.namespace)
        for _ in range(20):
            time.sleep(1)
            cnt = len(KPod(k8s_client).ops_batch.list({"app": wl_app.name}, namespace=wl_app.namespace).items)
            if cnt == 0:
                break
        else:
            pytest.fail("delete collection failed")

    def test_delete_individual(self, k8s_client, wl_app):
        KPod(k8s_client).create_or_update(
            wl_app.scheduler_safe_name,
            namespace=wl_app.namespace,
            body=construct_foo_pod(wl_app.scheduler_safe_name, labels={"app": wl_app.name}),
        )
        assert len(KPod(k8s_client).ops_batch.list({"app": wl_app.name}, namespace=wl_app.namespace).items) == 1
        KPod(k8s_client).ops_batch.delete_individual(
            {"app": wl_app.name}, namespace=wl_app.namespace, non_grace_period=False
        )
        for _ in range(20):
            time.sleep(1)
            cnt = len(KPod(k8s_client).ops_batch.list({"app": wl_app.name}, namespace=wl_app.namespace).items)
            if cnt == 0:
                break
        else:
            pytest.fail("delete individual failed")

    @pytest.mark.parametrize(
        ("input_dict", "expected_output"),
        [
            ({}, ""),
            ({"level1": {"level2": {"field": "value"}}}, "level1.level2.field=value"),
            ({"level1": {"level2": {"level3": {"field": "value"}}}}, "level1.level2.level3.field=value"),
            (
                {"level1": "simple_value", "level2": {"subfield": "sub_value"}},
                "level1=simple_value,level2.subfield=sub_value",
            ),
        ],
    )
    def test_make_fields_string(self, input_dict, expected_output):
        assert BatchOperations.make_fields_string(input_dict) == expected_output


class TestKNamespace:
    def test_has_default_sa_with_or_without_secrets(self, k8s_client, resource_name):
        namespace = resource_name
        KNamespace(k8s_client).get_or_create(namespace)

        # Create default SA
        sa_body: Dict[str, Any] = {"kind": "ServiceAccount", "metadata": {"name": "default"}}
        KServiceAccount(k8s_client).create_or_update("default", body=sa_body, namespace=namespace)
        assert KNamespace(k8s_client).default_sa_exists(namespace) is True

        KNamespace(k8s_client).delete(namespace)

    def test_wait_for_default_sa_failed(self, k8s_client, resource_name):
        cli = KNamespace(k8s_client)
        time_started = time.time()
        namespace = resource_name
        with (
            pytest.raises(CreateServiceAccountTimeout),
            mock.patch.object(KNamespace, "default_sa_exists", return_value=False),
        ):
            assert cli.wait_for_default_sa(namespace, timeout=2, check_period=0.1)

        assert math.isclose(time.time(), time_started, abs_tol=2.1)

    def test_wait_for_default_sa_succeed(self, k8s_client, resource_name):
        namespace = resource_name

        obj, created = KNamespace(k8s_client).get_or_create(namespace)
        assert obj.metadata.name == namespace
        assert created is True

        # Create default SA
        sa_body: Dict[str, Any] = {"kind": "ServiceAccount", "metadata": {"name": "default"}}
        KServiceAccount(k8s_client).create_or_update("default", body=sa_body, namespace=namespace)
        assert KNamespace(k8s_client).wait_for_default_sa(namespace, timeout=1) is None

        KNamespace(k8s_client).delete(namespace)


@pytest.mark.auto_create_ns
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

    def test_wait_for_status_normal(self, k8s_client, wl_app):
        KPod(k8s_client).create_or_update(
            wl_app.scheduler_safe_name, namespace=wl_app.namespace, body=construct_foo_pod(wl_app.scheduler_safe_name)
        )
        # Default status should be "Pending"
        assert (
            KPod(k8s_client).wait_for_status(
                wl_app.scheduler_safe_name,
                ["Pending"],
                namespace=wl_app.namespace,
                timeout=0.2,
            )
            == "Pending"
        )

    def test_get_logs(self, k8s_client, wl_app):
        KPod(k8s_client).create_or_update(
            wl_app.scheduler_safe_name,
            namespace=wl_app.namespace,
            body=construct_foo_pod(wl_app.scheduler_safe_name, restart_policy="Never"),
        )
        logs = KPod(k8s_client).get_log(wl_app.scheduler_safe_name, namespace=wl_app.namespace, timeout=0.1)
        assert logs is not None


class TestKDeployment:
    def test_restart(self, k8s_client, namespace_maker, resource_name):
        namespace = resource_name
        namespace_maker.make(namespace)

        deployment_body = construct_foo_deployment(resource_name, KDeployment(k8s_client).get_preferred_version())
        KDeployment(k8s_client).create_or_update(resource_name, namespace=namespace, body=deployment_body)

        restart_deployment = KDeployment(k8s_client).restart(name=resource_name, namespace=namespace)
        assert restart_deployment.spec.template.metadata.annotations[KUBECTL_RESTART_RESOURCE_KEY] is not None


#########
# Utils #
#########


def construct_foo_deployment(name: str, api_version: str = "extensions/v1beta1") -> Dict:
    manifest = yaml.safe_load(
        dedent(
            """\
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
                    automountServiceAccountToken: false
                    containers:
                    - name: main
                      image: busybox
    """.format(api_version=api_version, name=name)
        )
    )
    return manifest


def construct_foo_pod(name: str, labels: Optional[Dict] = None, restart_policy: str = "Always") -> Dict:
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": name, "labels": labels or {}},
        "spec": {
            # Set "schedulerName", so the pod won't be processed by the default
            # scheduler.
            "schedulerName": "no-running-scheduler",
            "containers": [{"name": "main", "image": "busybox:latest", "imagePullPolicy": "IfNotPresent"}],
            "restartPolicy": restart_policy,
            "automountServiceAccountToken": False,
        },
    }
