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

"""集群侧的内存替身，以及各测试共用的常量与断言辅助"""

from contextlib import contextmanager
from types import SimpleNamespace

from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paasng.platform.agent_sandbox.e2b.constants import TEMPLATE_MANAGED_BY_LABEL, TEMPLATE_MANAGED_BY_VALUE
from paasng.platform.agent_sandbox.models import E2BSandboxTemplateSyncRecord

NAMESPACE = "e2b-system"
# 启用了 e2b，但不在测试租户的分配策略里
OTHER_CLUSTER = "e2b-other-cluster"
MANAGED_LABELS = {TEMPLATE_MANAGED_BY_LABEL: TEMPLATE_MANAGED_BY_VALUE}


class FakeClusters:
    """各集群里的 CR，按（集群, kind, 名称）存放清单"""

    def __init__(self):
        self.objects: dict[tuple[str, str, str], dict] = {}
        self.broken_clusters: set[str] = set()
        self.failing_names: set[str] = set()
        # 只有池子写入失败，同名的模板照常写入
        self.failing_pools: set[str] = set()

    def put(self, cluster: str, kind: str, name: str, labels: dict | None = None):
        self.objects[(cluster, kind, name)] = {"metadata": {"name": name, "labels": labels or {}}}

    def names(self, cluster: str, kind: str) -> set[str]:
        return {n for (c, k, n) in self.objects if c == cluster and k == kind}

    def manifest(self, cluster: str, kind: str, name: str) -> dict:
        return self.objects[(cluster, kind, name)]

    @contextmanager
    def client_for(self, cluster_name: str):
        if cluster_name in self.broken_clusters:
            raise RuntimeError(f"cluster {cluster_name} unreachable")
        yield cluster_name

    def kres(self, kres_cls, client: str):
        return _FakeResource(self, client, kres_cls.kind)


class _FakeResource:
    def __init__(self, clusters: FakeClusters, cluster: str, kind: str):
        self.clusters = clusters
        self.cluster = cluster
        self.kind = kind
        self.ops_batch = self

    def create_or_update(self, name, namespace, body, **kwargs):
        assert namespace == NAMESPACE
        if name in self.clusters.failing_names or (self.kind == "SandboxPool" and name in self.clusters.failing_pools):
            raise RuntimeError(f"admission webhook denied {name}")
        self.clusters.objects[(self.cluster, self.kind, name)] = body

    def get(self, name, namespace):
        try:
            manifest = self.clusters.objects[(self.cluster, self.kind, name)]
        except KeyError:
            raise ResourceMissing(namespace, name)
        return SimpleNamespace(to_dict=lambda: manifest)

    def delete(self, name, namespace):
        del self.clusters.objects[(self.cluster, self.kind, name)]

    def list(self, labels, namespace):
        items = []
        for (c, k, n), manifest in self.clusters.objects.items():
            obj_labels = manifest["metadata"].get("labels") or {}
            if c == self.cluster and k == self.kind and all(obj_labels.get(lk) == v for lk, v in labels.items()):
                items.append(SimpleNamespace(metadata=SimpleNamespace(name=n)))
        return SimpleNamespace(items=items)


class FakeLock:
    """进程内的锁替身，held 为真时相当于别的进程正持有锁"""

    def __init__(self):
        self.held = False

    @contextmanager
    def __call__(self, lock_key: str, timeout: int):
        if self.held:
            yield False
            return
        self.held = True
        try:
            yield True
        finally:
            self.held = False


def status_of(template) -> dict[str, str]:
    return {r.cluster_name: r.status for r in E2BSandboxTemplateSyncRecord.objects.filter(template=template)}


def image_of(clusters: FakeClusters, cluster: str, name: str) -> str:
    manifest = clusters.manifest(cluster, "SandboxTemplate", name)
    return manifest["spec"]["template"]["spec"]["podTemplate"]["containers"][0]["image"]
