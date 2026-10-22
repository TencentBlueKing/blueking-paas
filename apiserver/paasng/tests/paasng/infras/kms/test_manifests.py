# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from paasng.infras.kms import manifests

OPENBAO_KEY = "default/scope/blueking/secret/demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d"


def test_cluster_secret_store():
    store = manifests.build_cluster_secret_store(
        name="kms-x",
        server="https://openbao.example.com",
        kv_path="secret",
        auth_mount="kubernetes",
        role="default.scope.blueking.secret.x",
        namespace="ns-1",
        service_account_name="demo-web-prod-kms",
        mtls_secret_namespace="paas-system",
        mtls_secret_name="openbao-mtls-client",
        labels={},
    )

    assert "namespace" not in store["metadata"]
    # 只有应用所在 namespace 可以引用该 store
    assert store["spec"]["conditions"] == [{"namespaceRegexes": ["^ns\\-1$"]}]
    vault = store["spec"]["provider"]["vault"]
    assert vault["auth"]["kubernetes"]["serviceAccountRef"] == {"name": "demo-web-prod-kms", "namespace": "ns-1"}
    mtls_refs = [vault["caProvider"], vault["tls"]["certSecretRef"], vault["tls"]["keySecretRef"]]
    assert {(ref["namespace"], ref["name"]) for ref in mtls_refs} == {("paas-system", "openbao-mtls-client")}


def test_external_secret_maps_to_sdk_secret_keys():
    es = manifests.build_external_secret(
        name="kms-x",
        namespace="ns-1",
        store_name="kms-x",
        target_secret_name="kms-x",
        openbao_key=OPENBAO_KEY,
        refresh_interval="1h",
        labels={},
    )

    assert es["spec"]["secretStoreRef"] == {"name": "kms-x", "kind": "ClusterSecretStore"}
    assert es["spec"]["target"] == {"name": "kms-x", "creationPolicy": "Owner", "deletionPolicy": "Retain"}
    assert es["spec"]["data"] == [
        {"secretKey": "envelope", "remoteRef": {"key": OPENBAO_KEY, "property": "envelope"}},
        {"secretKey": "private-key", "remoteRef": {"key": OPENBAO_KEY, "property": "private_key"}},
    ]


def test_service_account_does_not_automount_token():
    sa = manifests.build_service_account(name="demo-web-prod-kms", namespace="ns-1", labels={})

    assert sa["automountServiceAccountToken"] is False
