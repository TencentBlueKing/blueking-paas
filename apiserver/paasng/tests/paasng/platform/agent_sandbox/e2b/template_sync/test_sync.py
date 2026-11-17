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
from paasng.platform.agent_sandbox.e2b.template_sync import records, status, sync
from paasng.platform.agent_sandbox.models import E2BSandboxTemplateSyncRecord
from tests.paasng.platform.agent_sandbox.e2b.helpers import make_builtin_template, make_custom_template
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .fakes import MANAGED_LABELS, OTHER_CLUSTER, image_of, status_of

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestSyncScopedTemplate:
    def test_builtin_goes_to_all_e2b_clusters(self, clusters):
        template = make_builtin_template("e2b-envd")

        sync.sync_templates(resource_names={"e2b-envd"})

        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert clusters.names(cluster, "SandboxTemplate") == {"e2b-envd"}
            assert clusters.names(cluster, "SandboxPool") == {"e2b-envd"}
        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.SUCCEEDED.value,
        }

    def test_custom_goes_only_to_allocatable_clusters(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")

        sync.sync_templates(resource_names={template.resource_name})

        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {template.resource_name}
        assert clusters.names(OTHER_CLUSTER, "SandboxPool") == set()

    def test_deleted_template_removes_managed_crs(self, clusters):
        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            for kind in ("SandboxTemplate", "SandboxPool"):
                clusters.put(cluster, kind, "gone", MANAGED_LABELS)

        results = sync.sync_templates(resource_names={"gone"})

        assert clusters.objects == {}
        assert all(r.pruned == ["gone"] for r in results)

    def test_deleted_template_keeps_unmanaged_crs(self, clusters):
        """集群里手工建的同名 CR 不归平台管"""
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "handmade")

        sync.sync_templates(resource_names={"handmade"})

        assert len(clusters.objects) == 2


class TestApplyResources:
    def test_update_keeps_metadata_written_by_controller(self, clusters):
        template = make_builtin_template("e2b-envd", image="old:v1")
        sync.sync_templates(resource_names={"e2b-envd"})
        for kind in ("SandboxTemplate", "SandboxPool"):
            metadata = clusters.manifest(CLUSTER_NAME_FOR_TESTING, kind, "e2b-envd")["metadata"]
            metadata["finalizers"] = ["sandbox.bkbcs.tencent.com/cleanup"]
            metadata["annotations"] = {"controller": "1"}

        type(template).objects.filter(pk=template.pk).update(image="new:v2")
        sync.sync_templates(resource_names={"e2b-envd"})

        assert image_of(clusters, CLUSTER_NAME_FOR_TESTING, "e2b-envd") == "new:v2"
        for kind in ("SandboxTemplate", "SandboxPool"):
            metadata = clusters.manifest(CLUSTER_NAME_FOR_TESTING, kind, "e2b-envd")["metadata"]
            assert metadata["finalizers"] == ["sandbox.bkbcs.tencent.com/cleanup"]
            assert metadata["annotations"] == {"controller": "1"}
            assert metadata["labels"] == MANAGED_LABELS

    def test_removing_disk_clears_its_fields(self, clusters):
        """merge patch 不删缺的键，去掉系统盘后集群里不能残留盘与 PVC"""
        template = make_builtin_template("e2b-envd", disk_size_mb=1000)
        sync.sync_templates(resource_names={"e2b-envd"})

        type(template).objects.filter(pk=template.pk).update(disk_size_mb=None)
        sync.sync_templates(resource_names={"e2b-envd"})

        manifest = clusters.manifest(CLUSTER_NAME_FOR_TESTING, "SandboxTemplate", "e2b-envd")
        spec = manifest["spec"]["template"]["spec"]
        assert "devices" not in spec["domain"]
        assert "volumes" not in spec["podTemplate"]
        assert "volumeClaimTemplates" not in spec


class TestSyncAll:
    def test_syncs_everything_and_prunes_stale(self, clusters, bk_app):
        make_builtin_template("e2b-envd")
        custom = make_custom_template(bk_app, "mine")
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "stale", MANAGED_LABELS)
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "handmade")

        results = {r.cluster_name: r for r in sync.sync_templates()}

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
        sync.sync_templates()
        snapshot = dict(clusters.objects)

        results = sync.sync_templates()

        assert clusters.objects == snapshot
        assert all(r.pruned == [] and r.failed == {} and r.error == "" for r in results)

    def test_template_failure_is_isolated(self, clusters):
        make_builtin_template("e2b-envd")
        bad = make_builtin_template("e2b-bad")
        clusters.failing_names.add("e2b-bad")

        results = {r.cluster_name: r for r in sync.sync_templates()}

        main = results[CLUSTER_NAME_FOR_TESTING]
        assert main.synced == ["e2b-envd"]
        assert "admission webhook" in main.failed["e2b-bad"]
        assert status_of(bad)[CLUSTER_NAME_FOR_TESTING] == E2BTemplateSyncStatus.FAILED.value

    def test_cluster_failure_is_isolated(self, clusters):
        template = make_builtin_template("e2b-envd")
        records.mark_pending(template)
        clusters.broken_clusters.add(OTHER_CLUSTER)

        results = {r.cluster_name: r for r in sync.sync_templates()}

        assert "unreachable" in results[OTHER_CLUSTER].error
        assert results[CLUSTER_NAME_FOR_TESTING].synced == ["e2b-envd"]
        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {"e2b-envd"}
        # 连不上的集群也要落成失败，不能残留成待同步
        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.FAILED.value,
        }

    def test_skips_and_prunes_non_target_clusters(self, clusters):
        """保存之后才停用 e2b 的集群不再下发，它的记录收尾时清理，不会一直挂着待同步"""
        template = make_builtin_template("e2b-envd")
        records.mark_pending(template)
        E2BSandboxTemplateSyncRecord.objects.create(template=template, cluster_name="retired", status="succeeded")
        ClusterE2BConfig.objects.filter(cluster__name=OTHER_CLUSTER).update(enabled=False)

        sync.sync_templates()

        assert clusters.names(OTHER_CLUSTER, "SandboxPool") == set()
        assert status_of(template) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value}

    def test_fills_records_of_newly_enabled_cluster(self, clusters):
        """之后才启用 e2b 的集群原本没有记录，全量同步后补齐"""
        template = make_builtin_template("e2b-envd")
        assert status.get_cluster_overviews()[0].missing == ["e2b-envd"]

        sync.sync_templates()

        assert all(o.completed for o in status.get_cluster_overviews())
        assert status.get_template_overviews([template])[0].status == E2BTemplateSyncStatus.SUCCEEDED.value

    def test_refuses_while_another_sync_runs(self, clusters, sync_lock):
        make_builtin_template("e2b-envd")
        sync_lock.held = True

        with pytest.raises(E2BTemplateSyncInProgress):
            sync.sync_templates()
        assert clusters.objects == {}

    def test_scoped_to_clusters(self, clusters):
        """范围外集群的记录不动，不能被当成不再是目标而删掉"""
        template = make_builtin_template("e2b-envd")
        records.mark_pending(template)

        results = sync.sync_templates(cluster_names={CLUSTER_NAME_FOR_TESTING})

        assert [r.cluster_name for r in results] == [CLUSTER_NAME_FOR_TESTING]
        assert clusters.names(OTHER_CLUSTER, "SandboxPool") == set()
        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }

    def test_scoped_to_templates_keeps_crs_out_of_scope(self, clusters):
        """只拿到一部分模板时，判断不了范围外多出来的 CR 是不是残留"""
        make_builtin_template("e2b-envd")
        make_builtin_template("e2b-other")
        for kind in ("SandboxTemplate", "SandboxPool"):
            clusters.put(CLUSTER_NAME_FOR_TESTING, kind, "stale", MANAGED_LABELS)

        results = {r.cluster_name: r for r in sync.sync_templates(resource_names={"e2b-envd"})}

        assert results[CLUSTER_NAME_FOR_TESTING].synced == ["e2b-envd"]
        assert results[CLUSTER_NAME_FOR_TESTING].pruned == []
        assert clusters.names(CLUSTER_NAME_FOR_TESTING, "SandboxPool") == {"e2b-envd", "stale"}

    def test_keeps_template_created_during_sync(self, clusters, race_after_first_apply):
        """开始同步后才新建并下发完成的模板，不能被当作已删除的清理掉"""
        make_builtin_template("e2b-envd")

        def _create_and_push():
            make_builtin_template("e2b-new")
            sync._sync_templates(None, {"e2b-new"})

        race_after_first_apply(_create_and_push)
        results = sync.sync_templates()

        assert all(r.pruned == [] for r in results)
        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert clusters.names(cluster, "SandboxPool") == {"e2b-envd", "e2b-new"}

    def test_pushes_latest_spec_of_template_changed_during_sync(self, clusters, race_after_first_apply):
        template = make_builtin_template("e2b-envd", image="old:v1")

        def _change_and_push():
            type(template).objects.filter(pk=template.pk).update(image="new:v2")
            sync._sync_templates(None, {"e2b-envd"})

        race_after_first_apply(_change_and_push)
        sync.sync_templates()

        for cluster in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
            assert image_of(clusters, cluster, "e2b-envd") == "new:v2"

    def test_skips_template_deleted_during_sync(self, clusters, race_after_first_apply):
        """同步途中被删除、CR 已清理的模板，不能再下发回去，也不留下记录"""
        template = make_builtin_template("e2b-envd")

        def _delete_and_cleanup():
            template.delete()
            sync._sync_templates(None, {"e2b-envd"})

        race_after_first_apply(_delete_and_cleanup)
        sync.sync_templates()

        assert clusters.objects == {}
        assert not E2BSandboxTemplateSyncRecord.objects.exists()
