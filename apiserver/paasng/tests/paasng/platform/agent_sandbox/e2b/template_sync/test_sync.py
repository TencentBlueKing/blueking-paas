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

import pytest

from paas_wl.infras.cluster.models import ClusterE2BConfig
from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.exceptions import E2BTemplateSyncInProgress
from paasng.platform.agent_sandbox.e2b.template_sync import status, sync
from paasng.platform.agent_sandbox.models import E2BSandboxTemplateSyncRecord
from tests.paasng.platform.agent_sandbox.e2b.helpers import make_builtin_template, make_custom_template
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .fakes import MANAGED_LABELS, OTHER_CLUSTER, image_of, status_of

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestMarkPending:
    def test_marks_target_clusters_pending(self, bk_app):
        builtin = make_builtin_template("e2b-envd")
        custom = make_custom_template(bk_app, "mine")

        sync.mark_pending(builtin)
        sync.mark_pending(custom)

        assert status_of(builtin) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.PENDING.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }
        assert status_of(custom) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.PENDING.value}

    def test_overwrites_previous_result_and_drops_non_targets(self):
        template = make_builtin_template("e2b-envd")
        E2BSandboxTemplateSyncRecord.objects.create(
            template=template, cluster_name=CLUSTER_NAME_FOR_TESTING, status="failed", message="boom"
        )
        E2BSandboxTemplateSyncRecord.objects.create(template=template, cluster_name="retired", status="succeeded")

        sync.mark_pending(template)

        record = E2BSandboxTemplateSyncRecord.objects.get(template=template, cluster_name=CLUSTER_NAME_FOR_TESTING)
        assert (record.status, record.message) == (E2BTemplateSyncStatus.PENDING.value, "")
        assert "retired" not in status_of(template)


class TestMarkSyncPending:
    def test_resets_records_not_current(self, clusters):
        """已成功下发当前配置的不动，同步期间要保持可用"""
        template = make_builtin_template("e2b-envd")
        changed = make_builtin_template("e2b-changed")
        clusters.broken_clusters.add(OTHER_CLUSTER)
        sync.sync_all()
        # 下发成功之后配置又变了，例如摘要算法调整后上线
        type(changed).objects.filter(pk=changed.pk).update(image="new:v2")

        sync.mark_sync_pending()

        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }
        assert set(status_of(changed).values()) == {E2BTemplateSyncStatus.PENDING.value}
        assert set(
            E2BSandboxTemplateSyncRecord.objects.filter(template=template).values_list("message", flat=True)
        ) == {""}

    def test_only_resets_records_in_scope(self, clusters):
        template = make_builtin_template("e2b-envd")
        other = make_builtin_template("e2b-other")
        sync.sync_all()
        E2BSandboxTemplateSyncRecord.objects.update(status=E2BTemplateSyncStatus.FAILED.value)

        sync.mark_sync_pending(cluster_names={OTHER_CLUSTER}, resource_names={"e2b-envd"})

        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.FAILED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }
        assert set(status_of(other).values()) == {E2BTemplateSyncStatus.FAILED.value}


class TestForgetCluster:
    def test_drops_records_of_the_cluster_only(self, clusters):
        template = make_builtin_template("e2b-envd")
        sync.sync_all()

        sync.forget_cluster(OTHER_CLUSTER)

        assert status_of(template) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value}


class TestSyncTemplate:
    def test_builtin_goes_to_all_e2b_clusters(self, clusters):
        template = make_builtin_template("e2b-envd")

        sync.sync_template("e2b-envd")

        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert clusters.names(cluster, "SandboxTemplate") == {"e2b-envd"}
            assert clusters.names(cluster, "SandboxPool") == {"e2b-envd"}
        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.SUCCEEDED.value,
        }

    def test_custom_goes_only_to_allocatable_clusters(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")

        sync.sync_template(template.resource_name)

        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {template.resource_name}
        assert clusters.names(OTHER_CLUSTER, "SandboxPool") == set()

    def test_skips_disabled_e2b_clusters(self, clusters):
        template = make_builtin_template("e2b-envd")
        sync.mark_pending(template)
        ClusterE2BConfig.objects.filter(cluster__name=OTHER_CLUSTER).update(enabled=False)

        sync.sync_template("e2b-envd")

        assert clusters.names(OTHER_CLUSTER, "SandboxPool") == set()
        # 保存之后才停用的集群，下发时以当前为准，不会一直挂着待同步
        assert status_of(template) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value}

    def test_failure_is_recorded_without_affecting_others(self, clusters):
        template = make_builtin_template("e2b-envd")
        clusters.broken_clusters.add(OTHER_CLUSTER)

        sync.sync_template("e2b-envd")

        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {"e2b-envd"}
        record = E2BSandboxTemplateSyncRecord.objects.get(template=template, cluster_name=OTHER_CLUSTER)
        assert record.status == E2BTemplateSyncStatus.FAILED.value
        assert "unreachable" in record.message

    def test_resync_overwrites_status(self, clusters):
        template = make_builtin_template("e2b-envd")
        clusters.broken_clusters.add(OTHER_CLUSTER)
        sync.sync_template("e2b-envd")

        clusters.broken_clusters.clear()
        sync.sync_template("e2b-envd")

        assert status_of(template)[OTHER_CLUSTER] == E2BTemplateSyncStatus.SUCCEEDED.value

    def test_deleted_template_removes_managed_crs(self, clusters):
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "gone", MANAGED_LABELS)

        sync.sync_template("gone")

        assert clusters.objects == {}

    def test_deleted_template_keeps_unmanaged_crs(self, clusters):
        """集群里手工建的同名 CR 不归平台管"""
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "handmade")

        sync.sync_template("handmade")

        assert len(clusters.objects) == 2

    def test_refuses_while_another_sync_runs(self, clusters, sync_lock):
        make_builtin_template("e2b-envd")
        sync_lock.held = True

        with pytest.raises(E2BTemplateSyncInProgress):
            sync.sync_template("e2b-envd")
        assert clusters.objects == {}

    def test_stale_task_does_not_overwrite_newer_one(self, clusters, race_after_first_apply):
        """旧任务下发完第一个集群后，新任务把新配置下发完，旧任务继续时要用新配置"""
        template = make_builtin_template("e2b-envd", image="old:v1")

        def _newer_task():
            type(template).objects.filter(pk=template.pk).update(image="new:v2")
            sync._sync_template("e2b-envd")

        race_after_first_apply(_newer_task)
        sync.sync_template("e2b-envd")

        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert image_of(clusters, cluster, "e2b-envd") == "new:v2"


class TestSyncAll:
    def test_syncs_everything_and_prunes_stale(self, clusters, bk_app):
        make_builtin_template("e2b-envd")
        custom = make_custom_template(bk_app, "mine")
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "stale", MANAGED_LABELS)
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "handmade")

        results = {r.cluster_name: r for r in sync.sync_all()}

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
        sync.sync_all()
        snapshot = dict(clusters.objects)

        results = sync.sync_all()

        assert clusters.objects == snapshot
        assert all(r.pruned == [] and r.failed == {} and r.error == "" for r in results)

    def test_template_failure_is_isolated(self, clusters):
        make_builtin_template("e2b-envd")
        bad = make_builtin_template("e2b-bad")
        clusters.failing_names.add("e2b-bad")

        results = {r.cluster_name: r for r in sync.sync_all()}

        main = results[CLUSTER_NAME_FOR_TESTING]
        assert main.synced == ["e2b-envd"]
        assert "admission webhook" in main.failed["e2b-bad"]
        assert status_of(bad)[CLUSTER_NAME_FOR_TESTING] == E2BTemplateSyncStatus.FAILED.value

    def test_cluster_failure_is_isolated(self, clusters):
        template = make_builtin_template("e2b-envd")
        sync.mark_pending(template)
        clusters.broken_clusters.add(OTHER_CLUSTER)

        results = {r.cluster_name: r for r in sync.sync_all()}

        assert "unreachable" in results[OTHER_CLUSTER].error
        assert results[CLUSTER_NAME_FOR_TESTING].synced == ["e2b-envd"]
        # 连不上的集群也要落成失败，不能残留成待同步
        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.FAILED.value,
        }

    def test_fills_records_of_newly_enabled_cluster(self, clusters):
        """之后才启用 e2b 的集群原本没有记录，全量同步后补齐"""
        template = make_builtin_template("e2b-envd")
        assert status.get_cluster_overviews()[0].missing == ["e2b-envd"]

        sync.sync_all()

        assert all(o.completed for o in status.get_cluster_overviews())
        assert status.get_template_overviews([template])[0].status == E2BTemplateSyncStatus.SUCCEEDED.value

    def test_refuses_while_another_sync_runs(self, clusters, sync_lock):
        make_builtin_template("e2b-envd")
        sync_lock.held = True

        with pytest.raises(E2BTemplateSyncInProgress):
            sync.sync_all()
        assert clusters.objects == {}

    def test_scoped_to_clusters(self, clusters):
        """范围外集群的记录不动，不能被当成不再是目标而删掉"""
        template = make_builtin_template("e2b-envd")
        sync.mark_pending(template)

        results = sync.sync_all(cluster_names={CLUSTER_NAME_FOR_TESTING})

        assert [r.cluster_name for r in results] == [CLUSTER_NAME_FOR_TESTING]
        assert clusters.names(OTHER_CLUSTER, "SandboxPool") == set()
        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }

    def test_scoped_to_templates_skips_prune(self, clusters):
        """只拿到一部分模板时，判断不了集群里多出来的 CR 是不是残留"""
        make_builtin_template("e2b-envd")
        make_builtin_template("e2b-other")
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "stale", MANAGED_LABELS)

        results = {r.cluster_name: r for r in sync.sync_all(resource_names={"e2b-envd"})}

        assert results[CLUSTER_NAME_FOR_TESTING].synced == ["e2b-envd"]
        assert results[CLUSTER_NAME_FOR_TESTING].pruned == []
        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {"e2b-envd", "stale"}

    def test_keeps_template_created_during_sync(self, clusters, race_after_first_apply):
        """开始同步后才新建并下发完成的模板，不能被当作已删除的清理掉"""
        make_builtin_template("e2b-envd")

        def _create_and_push():
            make_builtin_template("e2b-new")
            sync._sync_template("e2b-new")

        race_after_first_apply(_create_and_push)
        results = sync.sync_all()

        assert all(r.pruned == [] for r in results)
        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert clusters.names(cluster, "SandboxPool") == {"e2b-envd", "e2b-new"}

    def test_pushes_latest_spec_of_template_changed_during_sync(self, clusters, race_after_first_apply):
        template = make_builtin_template("e2b-envd", image="old:v1")

        def _change_and_push():
            type(template).objects.filter(pk=template.pk).update(image="new:v2")
            sync._sync_template("e2b-envd")

        race_after_first_apply(_change_and_push)
        sync.sync_all()

        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert image_of(clusters, cluster, "e2b-envd") == "new:v2"

    def test_skips_template_deleted_during_sync(self, clusters, race_after_first_apply):
        """同步途中被删除、CR 已清理的模板，不能再下发回去，也不留下记录"""
        template = make_builtin_template("e2b-envd")

        def _delete_and_cleanup():
            template.delete()
            sync._sync_template("e2b-envd")

        race_after_first_apply(_delete_and_cleanup)
        sync.sync_all()

        assert clusters.objects == {}
        assert not E2BSandboxTemplateSyncRecord.objects.exists()
