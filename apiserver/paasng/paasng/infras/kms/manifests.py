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

"""KMS 相关 Kubernetes 资源的 manifest 构造

纯函数，只返回 dict，不访问集群。字段结构与 bk-apigateway 的 ESO 示例保持一致，并按计划改为：
- SecretStore 改为集群级 ClusterSecretStore，mTLS 证书引用平台 namespace 中唯一的一份；
- 不设置 conditions，SaaS 之间的隔离由 OpenBao role 绑定 SA 名与 namespace 保证；
- serviceAccountRef 不写 namespace，ESO 使用 ExternalSecret 所在 namespace 的专用 SA 登录。
"""

from typing import Any

from .constants import (
    MTLS_SECRET_KEY_CA,
    MTLS_SECRET_KEY_CERT,
    MTLS_SECRET_KEY_PRIVATE_KEY,
    OPENBAO_ENVELOPE_PROPERTY,
    OPENBAO_PRIVATE_KEY_PROPERTY,
    SECRET_KEY_ENVELOPE,
    SECRET_KEY_PRIVATE_KEY,
)

EXTERNAL_SECRETS_API_VERSION = "external-secrets.io/v1beta1"
CLUSTER_SECRET_STORE_KIND = "ClusterSecretStore"
EXTERNAL_SECRET_KIND = "ExternalSecret"


def build_service_account(*, name: str, namespace: str, labels: dict[str, str]) -> dict[str, Any]:
    """ESO 登录 OpenBao 使用的专用 SA。不挂载 token，身份由 ESO 通过 TokenRequest 获取"""
    return {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {"name": name, "namespace": namespace, "labels": dict(labels)},
        "automountServiceAccountToken": False,
    }


def build_cluster_secret_store(
    *,
    name: str,
    server: str,
    kv_path: str,
    auth_mount: str,
    role: str,
    service_account_name: str,
    mtls_secret_namespace: str,
    mtls_secret_name: str,
    labels: dict[str, str],
) -> dict[str, Any]:
    """集群级 SecretStore，每个凭证（即每个配置版本）一份，role 与凭证一一对应

    TODO(kms): 不复用的前提下，每次带敏感变量的部署都会新增一个集群级 ClusterSecretStore，
    数量会随部署增长。当前只靠人工清理，待评估自动回收或复用方案。

    serviceAccountRef 刻意不写 namespace，ESO 会使用引用它的 ExternalSecret 所在 namespace 中的同名 SA 登录。
    """
    return {
        "apiVersion": EXTERNAL_SECRETS_API_VERSION,
        "kind": CLUSTER_SECRET_STORE_KIND,
        "metadata": {"name": name, "labels": dict(labels)},
        "spec": {
            "provider": {
                "vault": {
                    "server": server,
                    "path": kv_path,
                    "version": "v2",
                    "caProvider": {
                        "type": "Secret",
                        "name": mtls_secret_name,
                        "namespace": mtls_secret_namespace,
                        "key": MTLS_SECRET_KEY_CA,
                    },
                    "tls": {
                        "certSecretRef": {
                            "name": mtls_secret_name,
                            "namespace": mtls_secret_namespace,
                            "key": MTLS_SECRET_KEY_CERT,
                        },
                        "keySecretRef": {
                            "name": mtls_secret_name,
                            "namespace": mtls_secret_namespace,
                            "key": MTLS_SECRET_KEY_PRIVATE_KEY,
                        },
                    },
                    "auth": {
                        "kubernetes": {
                            "mountPath": auth_mount,
                            "role": role,
                            "serviceAccountRef": {"name": service_account_name},
                        }
                    },
                }
            }
        },
    }


def build_external_secret(
    *,
    name: str,
    namespace: str,
    store_name: str,
    target_secret_name: str,
    openbao_key: str,
    refresh_interval: str,
    labels: dict[str, str],
) -> dict[str, Any]:
    """ExternalSecret：把 OpenBao 中同一条凭证的 envelope 与 private_key 同步为 Secret 的两个字段

    - creationPolicy 为 Owner：Secret 带 ownerReference 指向本 ExternalSecret，ExternalSecret 删除后由 GC 回收 Secret；
    - deletionPolicy 为 Retain（显式写出，与 ESO 默认值一致）：OpenBao 中的凭证消失时保留 Secret 并让 ExternalSecret 报错，
      避免运行中的 Pod 因 Secret 被删而无法重新挂载；
    - 该资源不归 BkApp 所有。
    """
    return {
        "apiVersion": EXTERNAL_SECRETS_API_VERSION,
        "kind": EXTERNAL_SECRET_KIND,
        "metadata": {"name": name, "namespace": namespace, "labels": dict(labels)},
        "spec": {
            "refreshInterval": refresh_interval,
            "secretStoreRef": {"name": store_name, "kind": CLUSTER_SECRET_STORE_KIND},
            "target": {"name": target_secret_name, "creationPolicy": "Owner", "deletionPolicy": "Retain"},
            "data": [
                {
                    "secretKey": SECRET_KEY_ENVELOPE,
                    "remoteRef": {"key": openbao_key, "property": OPENBAO_ENVELOPE_PROPERTY},
                },
                {
                    "secretKey": SECRET_KEY_PRIVATE_KEY,
                    "remoteRef": {"key": openbao_key, "property": OPENBAO_PRIVATE_KEY_PROPERTY},
                },
            ],
        },
    }
