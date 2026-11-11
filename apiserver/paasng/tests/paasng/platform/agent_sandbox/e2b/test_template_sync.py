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

"""模板下发到集群的行为验证。

集群侧用内存替身代替 k8s，集群与分配策略用真实数据，以覆盖「自定义模板只下发到应用租户可分配的集群」。
"""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from django_dynamic_fixture import G

from paas_wl.infras.cluster.models import Cluster, ClusterE2BConfig
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.agent_sandbox.e2b import template_sync
from paasng.platform.agent_sandbox.e2b.constants import (
    GATEWAY_TEMPLATE_LABEL,
    TEMPLATE_MANAGED_BY_LABEL,
    TEMPLATE_MANAGED_BY_VALUE,
    E2BTemplateStatus,
    E2BTemplateSyncStatus,
)
from paasng.platform.agent_sandbox.e2b.exceptions import E2BTemplateSyncInProgress
from paasng.platform.agent_sandbox.models import E2BSandboxTemplateSyncRecord
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .helpers import IMAGE, make_builtin_template, make_custom_template

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

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
        if name in self.clusters.failing_names:
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


@pytest.fixture()
def clusters(monkeypatch) -> FakeClusters:
    fake = FakeClusters()
    monkeypatch.setattr(template_sync, "get_client_by_cluster_name", fake.client_for)
    monkeypatch.setattr(template_sync, "_kres", fake.kres)
    return fake


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


@pytest.fixture(autouse=True)
def sync_lock(monkeypatch) -> FakeLock:
    lock = FakeLock()
    monkeypatch.setattr(template_sync, "redis_lock", lock)
    return lock


@pytest.fixture()
def race_after_first_apply(monkeypatch):
    """在第一次下发完成后插入一段操作，模拟锁过期后另一次下发与当前下发交错执行"""

    def _install(action):
        original = template_sync._apply
        pending = [action]

        def _apply(client, template, namespace):
            original(client, template, namespace)
            if pending:
                pending.pop()()

        monkeypatch.setattr(template_sync, "_apply", _apply)

    return _install


@pytest.fixture(autouse=True)
def e2b_clusters():
    for name in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
        cluster = Cluster.objects.filter(name=name).first() or G(Cluster, name=name, tenant_id=DEFAULT_TENANT_ID)
        ClusterE2BConfig.objects.create(
            cluster=cluster,
            control_plane_url="http://e2b-gateway:8080",
            data_plane_address="e2b.example.com",
            api_key="key",
            tenant_id=DEFAULT_TENANT_ID,
            namespace=NAMESPACE,
        )


def _status_of(template) -> dict[str, str]:
    return {r.cluster_name: r.status for r in E2BSandboxTemplateSyncRecord.objects.filter(template=template)}


def _image_of(clusters: FakeClusters, cluster: str, name: str) -> str:
    manifest = clusters.manifest(cluster, "SandboxTemplate", name)
    return manifest["spec"]["template"]["spec"]["podTemplate"]["containers"][0]["image"]


class TestManifests:
    def test_template_manifest(self, settings):
        settings.AGENT_SANDBOX_E2B_TEMPLATE_STORAGE_CLASS = "cbs-ssd"
        template = make_builtin_template(
            "e2b-envd", cpu_count=4, memory_mb=8192, disk_size_mb=1000, env_vars={"B": "2", "A": "1"}, workdir="/w"
        )

        manifest = template_sync.build_template_manifest(template, NAMESPACE)

        assert manifest["kind"] == "SandboxTemplate"
        assert manifest["metadata"] == {"name": "e2b-envd", "namespace": NAMESPACE, "labels": MANAGED_LABELS}
        spec = manifest["spec"]["template"]
        assert spec["metadata"]["labels"] == {GATEWAY_TEMPLATE_LABEL: "e2b-envd"}
        domain = spec["spec"]["domain"]
        assert domain["cpu"] == {"cores": 4}
        assert domain["memory"] == "8192Mi"
        assert domain["devices"]["disks"][0]["size"] == "1000Mi"
        (container,) = spec["spec"]["podTemplate"]["containers"]
        assert container["image"] == IMAGE
        assert container["env"] == [{"name": "A", "value": "1"}, {"name": "B", "value": "2"}]
        assert container["workingDir"] == "/w"
        (pvc,) = spec["spec"]["volumeClaimTemplates"]
        # 盘镜像文件放在 PVC 上，要给文件系统开销留余量
        assert pvc["spec"]["resources"]["requests"]["storage"] == "1500Mi"
        assert pvc["spec"]["storageClassName"] == "cbs-ssd"

    def test_omits_empty_optional_fields(self):
        """不填系统盘时，与集群里已有的 e2b-python 等模板一样，不声明盘与 PVC"""
        template = make_builtin_template("e2b-envd", disk_size_mb=None)

        spec = template_sync.build_template_manifest(template, NAMESPACE)["spec"]["template"]["spec"]

        assert spec["domain"] == {"cpu": {"cores": 2}, "memory": "4096Mi"}
        assert spec["podTemplate"] == {
            "containers": [{"name": "main", "image": IMAGE, "imagePullPolicy": "IfNotPresent"}]
        }
        assert "volumeClaimTemplates" not in spec

    def test_builtin_pool_is_prewarmed(self):
        template = make_builtin_template("e2b-envd", prewarm_count=3)

        manifest = template_sync.build_pool_manifest(template, NAMESPACE)

        assert manifest["metadata"]["labels"] == MANAGED_LABELS
        assert manifest["spec"] == {"replicas": 3, "templateRef": {"name": "e2b-envd"}}

    def test_custom_pool_is_cold(self, bk_app):
        """自定义模板不预热，网关在无库存时现场创建"""
        template = make_custom_template(bk_app, "mine", prewarm_count=5)

        manifest = template_sync.build_pool_manifest(template, NAMESPACE)

        assert manifest["spec"] == {"replicas": 0, "templateRef": {"name": template.resource_name}}


class TestMarkPending:
    def test_marks_target_clusters_pending(self, bk_app):
        builtin = make_builtin_template("e2b-envd")
        custom = make_custom_template(bk_app, "mine")

        template_sync.mark_pending(builtin)
        template_sync.mark_pending(custom)

        assert _status_of(builtin) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.PENDING.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }
        assert _status_of(custom) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.PENDING.value}

    def test_overwrites_previous_result_and_drops_non_targets(self):
        template = make_builtin_template("e2b-envd")
        E2BSandboxTemplateSyncRecord.objects.create(
            template=template, cluster_name=CLUSTER_NAME_FOR_TESTING, status="failed", message="boom"
        )
        E2BSandboxTemplateSyncRecord.objects.create(template=template, cluster_name="retired", status="succeeded")

        template_sync.mark_pending(template)

        record = E2BSandboxTemplateSyncRecord.objects.get(template=template, cluster_name=CLUSTER_NAME_FOR_TESTING)
        assert (record.status, record.message) == (E2BTemplateSyncStatus.PENDING.value, "")
        assert "retired" not in _status_of(template)


class TestMarkSyncPending:
    def test_resets_existing_records(self, clusters):
        template = make_builtin_template("e2b-envd")
        clusters.broken_clusters.add(OTHER_CLUSTER)
        template_sync.sync_template("e2b-envd")

        template_sync.mark_sync_pending()

        records = E2BSandboxTemplateSyncRecord.objects.filter(template=template)
        assert {(r.status, r.message) for r in records} == {(E2BTemplateSyncStatus.PENDING.value, "")}
        assert records.count() == 2

    def test_only_resets_records_in_scope(self, clusters):
        template = make_builtin_template("e2b-envd")
        other = make_builtin_template("e2b-other")
        template_sync.sync_all()

        template_sync.mark_sync_pending(cluster_names={OTHER_CLUSTER}, resource_names={"e2b-envd"})

        assert _status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }
        assert set(_status_of(other).values()) == {E2BTemplateSyncStatus.SUCCEEDED.value}


class TestSyncTemplate:
    def test_builtin_goes_to_all_e2b_clusters(self, clusters):
        template = make_builtin_template("e2b-envd")

        template_sync.sync_template("e2b-envd")

        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert clusters.names(cluster, "SandboxTemplate") == {"e2b-envd"}
            assert clusters.names(cluster, "SandboxPool") == {"e2b-envd"}
        assert _status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.SUCCEEDED.value,
        }

    def test_custom_goes_only_to_allocatable_clusters(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")

        template_sync.sync_template(template.resource_name)

        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {template.resource_name}
        assert clusters.names(OTHER_CLUSTER, "SandboxPool") == set()

    def test_skips_disabled_e2b_clusters(self, clusters):
        template = make_builtin_template("e2b-envd")
        template_sync.mark_pending(template)
        ClusterE2BConfig.objects.filter(cluster__name=OTHER_CLUSTER).update(enabled=False)

        template_sync.sync_template("e2b-envd")

        assert clusters.names(OTHER_CLUSTER, "SandboxPool") == set()
        # 保存之后才停用的集群，下发时以当前为准，不会一直挂着待同步
        assert _status_of(template) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value}

    def test_failure_is_recorded_without_affecting_others(self, clusters):
        template = make_builtin_template("e2b-envd")
        clusters.broken_clusters.add(OTHER_CLUSTER)

        template_sync.sync_template("e2b-envd")

        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {"e2b-envd"}
        record = E2BSandboxTemplateSyncRecord.objects.get(template=template, cluster_name=OTHER_CLUSTER)
        assert record.status == E2BTemplateSyncStatus.FAILED.value
        assert "unreachable" in record.message

    def test_resync_overwrites_status(self, clusters):
        template = make_builtin_template("e2b-envd")
        clusters.broken_clusters.add(OTHER_CLUSTER)
        template_sync.sync_template("e2b-envd")

        clusters.broken_clusters.clear()
        template_sync.sync_template("e2b-envd")

        assert _status_of(template)[OTHER_CLUSTER] == E2BTemplateSyncStatus.SUCCEEDED.value

    def test_deleted_template_removes_managed_crs(self, clusters):
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "gone", MANAGED_LABELS)

        template_sync.sync_template("gone")

        assert clusters.objects == {}

    def test_deleted_template_keeps_unmanaged_crs(self, clusters):
        """集群里手工建的同名 CR 不归平台管"""
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "handmade")

        template_sync.sync_template("handmade")

        assert len(clusters.objects) == 2

    def test_refuses_while_another_sync_runs(self, clusters, sync_lock):
        make_builtin_template("e2b-envd")
        sync_lock.held = True

        with pytest.raises(E2BTemplateSyncInProgress):
            template_sync.sync_template("e2b-envd")
        assert clusters.objects == {}

    def test_stale_task_does_not_overwrite_newer_one(self, clusters, race_after_first_apply):
        """旧任务下发完第一个集群后，新任务把新配置下发完，旧任务继续时要用新配置"""
        template = make_builtin_template("e2b-envd", image="old:v1")

        def _newer_task():
            type(template).objects.filter(pk=template.pk).update(image="new:v2")
            template_sync._sync_template("e2b-envd")

        race_after_first_apply(_newer_task)
        template_sync.sync_template("e2b-envd")

        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert _image_of(clusters, cluster, "e2b-envd") == "new:v2"


class TestSyncAll:
    def test_syncs_everything_and_prunes_stale(self, clusters, bk_app):
        make_builtin_template("e2b-envd")
        custom = make_custom_template(bk_app, "mine")
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "stale", MANAGED_LABELS)
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "handmade")

        results = {r.cluster_name: r for r in template_sync.sync_all()}

        main = results[CLUSTER_NAME_FOR_TESTING]
        assert sorted(main.synced) == sorted(["e2b-envd", custom.resource_name])
        assert main.pruned == ["stale"]
        assert results[OTHER_CLUSTER].synced == ["e2b-envd"]
        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {
            "e2b-envd",
            custom.resource_name,
            "handmade",
        }

    def test_is_idempotent(self, clusters):
        make_builtin_template("e2b-envd")
        template_sync.sync_all()
        snapshot = dict(clusters.objects)

        results = template_sync.sync_all()

        assert clusters.objects == snapshot
        assert all(r.pruned == [] and r.failed == {} and r.error == "" for r in results)

    def test_template_failure_is_isolated(self, clusters):
        make_builtin_template("e2b-envd")
        bad = make_builtin_template("e2b-bad")
        clusters.failing_names.add("e2b-bad")

        results = {r.cluster_name: r for r in template_sync.sync_all()}

        main = results[CLUSTER_NAME_FOR_TESTING]
        assert main.synced == ["e2b-envd"]
        assert "admission webhook" in main.failed["e2b-bad"]
        assert _status_of(bad)[CLUSTER_NAME_FOR_TESTING] == E2BTemplateSyncStatus.FAILED.value

    def test_cluster_failure_is_isolated(self, clusters):
        template = make_builtin_template("e2b-envd")
        template_sync.mark_pending(template)
        clusters.broken_clusters.add(OTHER_CLUSTER)

        results = {r.cluster_name: r for r in template_sync.sync_all()}

        assert "unreachable" in results[OTHER_CLUSTER].error
        assert results[CLUSTER_NAME_FOR_TESTING].synced == ["e2b-envd"]
        # 连不上的集群也要落成失败，不能残留成待同步
        assert _status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.FAILED.value,
        }

    def test_fills_records_of_newly_enabled_cluster(self, clusters):
        """之后才启用 e2b 的集群原本没有记录，全量同步后补齐"""
        template = make_builtin_template("e2b-envd")
        assert template_sync.get_cluster_overviews()[0].missing == ["e2b-envd"]

        template_sync.sync_all()

        assert all(o.completed for o in template_sync.get_cluster_overviews())
        assert template_sync.get_template_overviews([template])[0].status == E2BTemplateSyncStatus.SUCCEEDED.value

    def test_refuses_while_another_sync_runs(self, clusters, sync_lock):
        make_builtin_template("e2b-envd")
        sync_lock.held = True

        with pytest.raises(E2BTemplateSyncInProgress):
            template_sync.sync_all()
        assert clusters.objects == {}

    def test_scoped_to_clusters(self, clusters):
        """范围外集群的记录不动，不能被当成不再是目标而删掉"""
        template = make_builtin_template("e2b-envd")
        template_sync.mark_pending(template)

        results = template_sync.sync_all(cluster_names={CLUSTER_NAME_FOR_TESTING})

        assert [r.cluster_name for r in results] == [CLUSTER_NAME_FOR_TESTING]
        assert clusters.names(OTHER_CLUSTER, "SandboxPool") == set()
        assert _status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }

    def test_scoped_to_templates_skips_prune(self, clusters):
        """只拿到一部分模板时，判断不了集群里多出来的 CR 是不是残留"""
        make_builtin_template("e2b-envd")
        make_builtin_template("e2b-other")
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "stale", MANAGED_LABELS)

        results = {r.cluster_name: r for r in template_sync.sync_all(resource_names={"e2b-envd"})}

        assert results[CLUSTER_NAME_FOR_TESTING].synced == ["e2b-envd"]
        assert results[CLUSTER_NAME_FOR_TESTING].pruned == []
        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {"e2b-envd", "stale"}

    def test_keeps_template_created_during_sync(self, clusters, race_after_first_apply):
        """开始同步后才新建并下发完成的模板，不能被当作已删除的清理掉"""
        make_builtin_template("e2b-envd")

        def _create_and_push():
            make_builtin_template("e2b-new")
            template_sync._sync_template("e2b-new")

        race_after_first_apply(_create_and_push)
        results = template_sync.sync_all()

        assert all(r.pruned == [] for r in results)
        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert clusters.names(cluster, "SandboxPool") == {"e2b-envd", "e2b-new"}

    def test_pushes_latest_spec_of_template_changed_during_sync(self, clusters, race_after_first_apply):
        template = make_builtin_template("e2b-envd", image="old:v1")

        def _change_and_push():
            type(template).objects.filter(pk=template.pk).update(image="new:v2")
            template_sync._sync_template("e2b-envd")

        race_after_first_apply(_change_and_push)
        template_sync.sync_all()

        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert _image_of(clusters, cluster, "e2b-envd") == "new:v2"

    def test_skips_template_deleted_during_sync(self, clusters, race_after_first_apply):
        """同步途中被删除、CR 已清理的模板，不能再下发回去，也不留下记录"""
        template = make_builtin_template("e2b-envd")

        def _delete_and_cleanup():
            template.delete()
            template_sync._sync_template("e2b-envd")

        race_after_first_apply(_delete_and_cleanup)
        template_sync.sync_all()

        assert clusters.objects == {}
        assert not E2BSandboxTemplateSyncRecord.objects.exists()


class TestOverviews:
    def test_template_status_follows_worst_cluster(self, clusters):
        template = make_builtin_template("e2b-envd")
        template_sync.mark_pending(template)

        def _status():
            refreshed = type(template).objects.prefetch_related("sync_records").get(pk=template.pk)
            return template_sync.get_template_overviews([refreshed])[0].status

        assert _status() == E2BTemplateSyncStatus.PENDING.value

        clusters.broken_clusters.add(OTHER_CLUSTER)
        template_sync.sync_template("e2b-envd")
        assert _status() == E2BTemplateSyncStatus.FAILED.value

        clusters.broken_clusters.clear()
        template_sync.sync_template("e2b-envd")
        assert _status() == E2BTemplateSyncStatus.SUCCEEDED.value

    def test_template_without_target_cluster(self, bk_app):
        ClusterE2BConfig.objects.update(enabled=False)
        template = make_custom_template(bk_app, "mine")

        (overview,) = template_sync.get_template_overviews([template])

        assert (overview.status, overview.records, overview.missing) == (None, [], [])


class TestTemplateStatuses:
    """测试租户的首选集群是 CLUSTER_NAME_FOR_TESTING，OTHER_CLUSTER 不在它的分配策略里"""

    @staticmethod
    def _status(app, template) -> E2BTemplateStatus:
        template = type(template).objects.get(pk=template.pk)
        return template_sync.get_template_statuses(app, [template])[template.resource_name]

    def test_available_once_applied(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")
        template_sync.mark_pending(template)
        assert self._status(bk_app, template) == E2BTemplateStatus.SYNCING

        template_sync.sync_template(template.resource_name)

        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_changed_spec_is_syncing_until_applied(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")
        template_sync.sync_template(template.resource_name)

        template.image = "new:v2"
        template.save()
        template_sync.mark_pending(template)
        assert self._status(bk_app, template) == E2BTemplateStatus.SYNCING

        template_sync.sync_template(template.resource_name)
        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_non_spec_change_keeps_available(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")
        template_sync.sync_template(template.resource_name)

        type(template).objects.filter(pk=template.pk).update(name="renamed", description="changed")

        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_resync_keeps_available(self, clusters, bk_app):
        """运维重新同步会先置为待同步，失败了集群里也还是当前配置，都不影响使用"""
        template = make_custom_template(bk_app, "mine")
        template_sync.sync_template(template.resource_name)

        template_sync.mark_sync_pending()
        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

        clusters.broken_clusters.add(CLUSTER_NAME_FOR_TESTING)
        template_sync.sync_all()
        assert _status_of(template) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.FAILED.value}
        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_failed_push_of_current_spec(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")
        clusters.failing_names.add(template.resource_name)

        template_sync.sync_template(template.resource_name)

        assert self._status(bk_app, template) == E2BTemplateStatus.SYNC_FAILED

    def test_only_preferred_cluster_matters(self, clusters, bk_app):
        template = make_builtin_template("e2b-envd")
        clusters.broken_clusters.add(OTHER_CLUSTER)

        template_sync.sync_template("e2b-envd")

        assert _status_of(template)[OTHER_CLUSTER] == E2BTemplateSyncStatus.FAILED.value
        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_digest_follows_what_was_pushed(self, clusters, bk_app, race_after_first_apply):
        """下发途中模板又被修改：记录是成功，但集群里是修改前的配置，仍要等下一次下发"""
        template = make_custom_template(bk_app, "mine", image="old:v1")
        race_after_first_apply(lambda: type(template).objects.filter(pk=template.pk).update(image="new:v2"))

        template_sync.sync_template(template.resource_name)

        assert _status_of(template) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value}
        assert self._status(bk_app, template) == E2BTemplateStatus.SYNCING

    def test_no_cluster(self, bk_app):
        ClusterE2BConfig.objects.update(enabled=False)
        template = make_custom_template(bk_app, "mine")

        assert self._status(bk_app, template) == E2BTemplateStatus.NO_CLUSTER
