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
"""KMS 相关 Kubernetes 资源（ServiceAccount、ESO 资源与 Secret）的读写"""

from typing import Any, Dict, Optional, Protocol

from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import BaseKresource, KSecret, KServiceAccount
from paasng.infras.kms.manifests import CLUSTER_SECRET_STORE_KIND, EXTERNAL_SECRET_KIND

SECRET_API_VERSION = "v1"
SECRET_KIND = "Secret"


class KClusterSecretStore(BaseKresource):
    """ESO 集群级 SecretStore（external-secrets.io）"""

    kind = CLUSTER_SECRET_STORE_KIND


class KExternalSecret(BaseKresource):
    """ESO ExternalSecret（external-secrets.io）"""

    kind = EXTERNAL_SECRET_KIND


_KRES_BY_KIND: dict[str, type[BaseKresource]] = {
    "ServiceAccount": KServiceAccount,
    SECRET_KIND: KSecret,
    CLUSTER_SECRET_STORE_KIND: KClusterSecretStore,
    EXTERNAL_SECRET_KIND: KExternalSecret,
}


class KubeResourceClient(Protocol):
    def apply(self, manifest: Dict[str, Any]) -> str: ...

    def get(self, *, api_version: str, kind: str, name: str, namespace: Optional[str]) -> Optional[Dict[str, Any]]: ...


class KubeResources:
    """KubeResourceClient 的实现：在单个集群中读写资源，对外只使用普通 dict"""

    def __init__(self, client: Any):
        self._client = client

    @classmethod
    def for_cluster(cls, cluster_name: str) -> "KubeResources":
        return cls(get_client_by_cluster_name(cluster_name))

    def apply(self, manifest: Dict[str, Any]) -> str:
        """以 create_or_update 方式提交资源，返回 metadata.uid

        更新时使用 replace，CRD 资源的 replace 必须携带 resourceVersion，因此由 auto_add_version 自动补齐。
        """
        metadata = manifest["metadata"]
        kres = self._get_kres(manifest["apiVersion"], manifest["kind"])
        obj, _created = kres.create_or_update(
            metadata["name"], namespace=metadata.get("namespace"), body=manifest, auto_add_version=True
        )
        return str(obj.to_dict()["metadata"]["uid"])

    def get(self, *, api_version: str, kind: str, name: str, namespace: Optional[str]) -> Optional[Dict[str, Any]]:
        """按名称读取资源，不存在时返回 None"""
        try:
            obj = self._get_kres(api_version, kind).get(name, namespace=namespace)
        except ResourceMissing:
            return None
        return obj.to_dict()

    def _get_kres(self, api_version: str, kind: str) -> BaseKresource:
        return _KRES_BY_KIND[kind](self._client, api_version=api_version)
