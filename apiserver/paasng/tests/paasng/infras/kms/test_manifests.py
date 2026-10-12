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

import json
from typing import Any

from paasng.infras.kms import manifests

ROLE = "default.scope.blueking.secret.demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d"
OPENBAO_KEY = "default/scope/blueking/secret/demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d"


def _build_store(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "name": "kms-default-demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d",
        "server": "https://openbao.default.svc:8200",
        "kv_path": "secret",
        "auth_mount": "kubernetes",
        "role": ROLE,
        "service_account_name": "demo-web-prod-kms",
        "mtls_secret_namespace": "default",
        "mtls_secret_name": "openbao-mtls-client",
        "labels": {"app": "demo"},
    }
    kwargs.update(overrides)
    return manifests.build_cluster_secret_store(**kwargs)


class TestClusterSecretStore:
    def test_is_cluster_scoped(self):
        store = _build_store()
        assert store["kind"] == "ClusterSecretStore"
        assert "namespace" not in store["metadata"]

    def test_vault_provider_fields(self):
        vault = _build_store()["spec"]["provider"]["vault"]
        assert vault["server"] == "https://openbao.default.svc:8200"
        assert vault["path"] == "secret"
        assert vault["version"] == "v2"
        assert vault["auth"]["kubernetes"] == {
            "mountPath": "kubernetes",
            "role": ROLE,
            "serviceAccountRef": {"name": "demo-web-prod-kms"},
        }

    def test_mtls_references_point_to_platform_secret(self):
        vault = _build_store()["spec"]["provider"]["vault"]
        assert vault["caProvider"] == {
            "type": "Secret",
            "name": "openbao-mtls-client",
            "namespace": "default",
            "key": "ca.crt",
        }
        assert vault["tls"]["certSecretRef"] == {
            "name": "openbao-mtls-client",
            "namespace": "default",
            "key": "tls.crt",
        }
        assert vault["tls"]["keySecretRef"] == {
            "name": "openbao-mtls-client",
            "namespace": "default",
            "key": "tls.key",
        }

    def test_no_conditions_so_any_namespace_can_reference_it(self):
        assert "conditions" not in json.dumps(_build_store())

    def test_service_account_ref_has_no_namespace(self):
        sa_ref = _build_store()["spec"]["provider"]["vault"]["auth"]["kubernetes"]["serviceAccountRef"]
        assert set(sa_ref) == {"name"}


class TestExternalSecret:
    def test_maps_envelope_and_private_key(self):
        es = manifests.build_external_secret(
            name="kms-x",
            namespace="ns-1",
            store_name="kms-x",
            target_secret_name="kms-x",
            openbao_key=OPENBAO_KEY,
            refresh_interval="1h",
            labels={},
        )
        assert es["kind"] == "ExternalSecret"
        assert es["metadata"]["namespace"] == "ns-1"
        assert es["spec"]["refreshInterval"] == "1h"
        assert es["spec"]["secretStoreRef"] == {"name": "kms-x", "kind": "ClusterSecretStore"}
        assert es["spec"]["target"] == {"name": "kms-x", "creationPolicy": "Owner", "deletionPolicy": "Retain"}
        assert es["spec"]["data"] == [
            {"secretKey": "envelope", "remoteRef": {"key": OPENBAO_KEY, "property": "envelope"}},
            {"secretKey": "privateKey", "remoteRef": {"key": OPENBAO_KEY, "property": "private_key"}},
        ]


class TestServiceAccount:
    def test_does_not_automount_token(self):
        sa = manifests.build_service_account(name="demo-web-prod-kms", namespace="ns-1", labels={})
        assert sa["kind"] == "ServiceAccount"
        assert sa["automountServiceAccountToken"] is False
