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

"""状态对账与孤儿清理。

安全窗口的判定基于「本任务首次观察到该实例」的时刻，测试因此直接往缓存里
写入首见时间来模拟已等待的时长，不需要冻结时钟。
"""

import logging
import time
import uuid

import pytest
from django.core.cache import cache
from django.utils import timezone

from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.agent_sandbox.e2b import reconcile
from paasng.platform.agent_sandbox.e2b.constants import E2BSandboxStatus
from paasng.platform.agent_sandbox.e2b.exceptions import E2BGatewayUnavailable
from paasng.platform.agent_sandbox.models import E2BSandbox
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SAFETY_WINDOW_MINUTES = 10


@pytest.fixture(autouse=True)
def _isolated_cache(settings):
    """把缓存换成内存缓存"""
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": uuid.uuid4().hex}
    }
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _reconcile_settings(settings):
    settings.AGENT_SANDBOX_E2B_ORPHAN_CLEANUP_ENABLED = True
    settings.AGENT_SANDBOX_E2B_ORPHAN_SAFETY_WINDOW_MINUTES = SAFETY_WINDOW_MINUTES
    settings.AGENT_SANDBOX_E2B_TERMINATED_RETENTION_DAYS = 30


class FakeGateway:
    """网关替身，只需回答「现在还有哪些沙箱」并接受销毁。"""

    def __init__(self):
        self.items: list[dict] = []
        self.list_error: Exception | None = None
        self.kill_error: Exception | None = None
        self.killed: list[str] = []

    def __call__(self, config):
        return self

    def for_cluster(self, cluster_name: str):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def list_sandboxes(self):
        if self.list_error:
            raise self.list_error
        return [dict(item) for item in self.items]

    def kill_sandbox(self, sandbox_id):
        if self.kill_error:
            raise self.kill_error
        self.killed.append(sandbox_id)


@pytest.fixture()
def gateway(monkeypatch, e2b_config) -> FakeGateway:
    fake = FakeGateway()
    monkeypatch.setattr(reconcile, "E2BGatewayClient", fake)
    return fake


def _record(application, sandbox_id: str, status: str = E2BSandboxStatus.RUNNING.value, **overrides) -> E2BSandbox:
    return E2BSandbox.objects.create(
        sandbox_id=sandbox_id,
        application=application,
        cluster_name=CLUSTER_NAME_FOR_TESTING,
        status=status,
        tenant_id=DEFAULT_TENANT_ID,
        **overrides,
    )


def _gateway_item(sandbox_id: str, state: str = E2BSandboxStatus.RUNNING.value) -> dict:
    return {"sandboxID": sandbox_id, "state": state, "templateID": "e2b-envd"}


def _mark_orphan_seen_at(sandbox_id: str, seconds_ago: float) -> None:
    """伪造首见时间，模拟该孤儿已被观察了指定时长。"""
    cache.set(reconcile._ORPHAN_SEEN_KEY.format(sandbox_id=sandbox_id), time.time() - seconds_ago, timeout=None)


class TestStateConvergence:
    def test_gateway_no_longer_has_it(self, gateway, bk_app):
        """网关按空闲超时回收后，本地记录收敛为已终止。"""
        _record(bk_app, "reclaimed")

        result = reconcile.reconcile_all()

        assert result.converged == 1
        assert E2BSandbox.objects.get(sandbox_id="reclaimed").status == E2BSandboxStatus.TERMINATED.value

    def test_syncs_to_gateway_state(self, gateway, bk_app):
        """网关是权威来源，本地跟随它。"""
        _record(bk_app, "sbx-1")
        gateway.items = [_gateway_item("sbx-1", state=E2BSandboxStatus.PAUSED.value)]

        reconcile.reconcile_all()

        assert E2BSandbox.objects.get(sandbox_id="sbx-1").status == E2BSandboxStatus.PAUSED.value

    @pytest.mark.parametrize("local_status", [E2BSandboxStatus.RUNNING.value, E2BSandboxStatus.PAUSED.value])
    def test_unknown_state_keeps_local_status(self, gateway, bk_app, local_status):
        """网关给了不认识的状态时保留本地原状态。

        不能回退到某个具体状态：本地是 PAUSED 时，兜底成 RUNNING 会把「平台枚举
        落后于网关版本」写成用户记录上的一次假状态翻转。
        """
        _record(bk_app, "sbx-1", status=local_status)
        gateway.items = [_gateway_item("sbx-1", state="hibernating")]

        result = reconcile.reconcile_all()

        assert E2BSandbox.objects.get(sandbox_id="sbx-1").status == local_status
        assert result.converged == 0

    def test_unrecognized_states_are_logged_once_per_cluster(self, gateway, bk_app, caplog):
        """无法识别的状态按集群汇总成一条日志。

        逐条打的话，网关一升级就会每轮按沙箱数刷屏，而这里实际什么都没改。
        """
        for idx in range(3):
            _record(bk_app, f"sbx-{idx}")
        gateway.items = [_gateway_item(f"sbx-{idx}", state="hibernating") for idx in range(3)]

        with caplog.at_level(logging.WARNING, logger=reconcile.logger.name):
            reconcile.reconcile_all()

        unrecognized_logs = [r for r in caplog.records if "unrecognized states" in r.message]
        assert len(unrecognized_logs) == 1
        assert "3 sandbox(es)" in unrecognized_logs[0].getMessage()
        assert "hibernating" in unrecognized_logs[0].getMessage()

    def test_gateway_reported_terminated_is_honored(self, gateway, bk_app):
        """terminated 是已知取值，网关这么说就照它收敛，不算无法识别。"""
        _record(bk_app, "sbx-1")
        gateway.items = [_gateway_item("sbx-1", state=E2BSandboxStatus.TERMINATED.value)]

        result = reconcile.reconcile_all()

        assert E2BSandbox.objects.get(sandbox_id="sbx-1").status == E2BSandboxStatus.TERMINATED.value
        assert result.converged == 1

    def test_terminated_records_are_left_alone(self, gateway, bk_app):
        """已终止的记录不参与对账"""
        _record(bk_app, "dead", status=E2BSandboxStatus.TERMINATED.value)
        gateway.items = [_gateway_item("dead")]

        reconcile.reconcile_all()

        assert E2BSandbox.objects.get(sandbox_id="dead").status == E2BSandboxStatus.TERMINATED.value

    def test_dry_run_does_not_write(self, gateway, bk_app):
        _record(bk_app, "reclaimed")

        assert reconcile.reconcile_all(dry_run=True).converged == 1
        assert E2BSandbox.objects.get(sandbox_id="reclaimed").status == E2BSandboxStatus.RUNNING.value

    def test_bulk_update_refreshes_updated(self, gateway, bk_app):
        """bulk_update 不走 save()，必须显式写 updated，否则归档会按旧时间立刻清掉刚收敛的记录。"""
        record = _record(bk_app, "reclaimed")
        stale = timezone.now() - timezone.timedelta(days=60)
        E2BSandbox.objects.filter(pk=record.pk).update(updated=stale)

        before = timezone.now()
        reconcile.reconcile_all()

        refreshed = E2BSandbox.objects.get(sandbox_id="reclaimed")
        assert refreshed.status == E2BSandboxStatus.TERMINATED.value
        assert refreshed.updated >= before


class TestClusterFailureIsolation:
    def test_unreachable_gateway_leaves_records_untouched(self, gateway, bk_app):
        """集群连不上时保持沙箱状态"""
        _record(bk_app, "sbx-1")
        gateway.list_error = E2BGatewayUnavailable("gateway down")

        result = reconcile.reconcile_all()

        assert result.clusters_skipped == 1
        assert result.skipped_cluster_names == [CLUSTER_NAME_FOR_TESTING]
        assert E2BSandbox.objects.get(sandbox_id="sbx-1").status == E2BSandboxStatus.RUNNING.value


class TestOrphanCleanup:
    def test_killed_after_window_elapses(self, gateway):
        gateway.items = [_gateway_item("orphan")]
        _mark_orphan_seen_at("orphan", seconds_ago=SAFETY_WINDOW_MINUTES * 60 + 1)

        result = reconcile.reconcile_all()

        assert result.orphans_killed == 1
        assert gateway.killed == ["orphan"]

    def test_kept_within_window(self, gateway):
        gateway.items = [_gateway_item("orphan")]
        _mark_orphan_seen_at("orphan", seconds_ago=60)

        result = reconcile.reconcile_all()

        assert (result.orphans_killed, result.orphans_waiting) == (0, 1)
        assert gateway.killed == []

    def test_recorded_sandbox_is_not_an_orphan(self, gateway, bk_app):
        gateway.items = [_gateway_item("sbx-1")]
        _record(bk_app, "sbx-1")
        _mark_orphan_seen_at("sbx-1", seconds_ago=SAFETY_WINDOW_MINUTES * 60 + 1)

        reconcile.reconcile_all()

        assert gateway.killed == []

    def test_terminated_record_is_not_an_orphan(self, gateway, bk_app):
        """本地标记为终止而网关仍有，说明销毁没生效，不是无主实例。"""
        gateway.items = [_gateway_item("dead")]
        _record(bk_app, "dead", status=E2BSandboxStatus.TERMINATED.value)
        _mark_orphan_seen_at("dead", seconds_ago=SAFETY_WINDOW_MINUTES * 60 + 1)

        reconcile.reconcile_all()

        assert gateway.killed == []

    def test_dry_run_does_not_kill(self, gateway):
        gateway.items = [_gateway_item("orphan")]
        _mark_orphan_seen_at("orphan", seconds_ago=SAFETY_WINDOW_MINUTES * 60 + 1)

        assert reconcile.reconcile_all(dry_run=True).orphans_killed == 1
        assert gateway.killed == []

    def test_kill_failure_is_counted_and_retried_next_round(self, gateway):
        gateway.items = [_gateway_item("orphan")]
        gateway.kill_error = E2BGatewayUnavailable("gateway down")
        _mark_orphan_seen_at("orphan", seconds_ago=SAFETY_WINDOW_MINUTES * 60 + 1)

        result = reconcile.reconcile_all()

        assert (result.failures, result.orphans_killed) == (1, 0)
        # 首见时间没被清掉，下一轮直接重试而不必重新等窗口
        assert cache.get(reconcile._ORPHAN_SEEN_KEY.format(sandbox_id="orphan")) is not None


class TestArchive:
    def _age_record(self, record: E2BSandbox, days: int) -> None:
        # updated 是 auto_now，只能绕过 save 直接改
        E2BSandbox.objects.filter(pk=record.pk).update(updated=timezone.now() - timezone.timedelta(days=days))

    def test_removes_records_past_retention(self, bk_app):
        record = _record(bk_app, "old", status=E2BSandboxStatus.TERMINATED.value)
        self._age_record(record, days=31)

        assert reconcile.archive_terminated_sandboxes() == 1
        assert not E2BSandbox.objects.filter(sandbox_id="old").exists()

    def test_keeps_recent_terminated_records(self, bk_app):
        record = _record(bk_app, "recent", status=E2BSandboxStatus.TERMINATED.value)
        self._age_record(record, days=29)

        assert reconcile.archive_terminated_sandboxes() == 0

    def test_never_removes_active_records(self, bk_app):
        """保留期只对终止记录生效，跑了很久的活跃沙箱不能被当成过期数据删掉。"""
        record = _record(bk_app, "long-running")
        self._age_record(record, days=365)

        assert reconcile.archive_terminated_sandboxes() == 0
        assert E2BSandbox.objects.filter(sandbox_id="long-running").exists()

    def test_dry_run_only_counts(self, bk_app):
        record = _record(bk_app, "old", status=E2BSandboxStatus.TERMINATED.value)
        self._age_record(record, days=31)

        assert reconcile.archive_terminated_sandboxes(dry_run=True) == 1
        assert E2BSandbox.objects.filter(sandbox_id="old").exists()

    def test_deletes_beyond_a_single_batch(self, bk_app, monkeypatch):
        """归档分批执行，一批装不下时要继续删完而不是只删第一批。"""
        monkeypatch.setattr(reconcile, "ARCHIVE_BATCH_SIZE", 2)
        for idx in range(5):
            record = _record(bk_app, f"old-{idx}", status=E2BSandboxStatus.TERMINATED.value)
            self._age_record(record, days=31)

        assert reconcile.archive_terminated_sandboxes() == 5
        assert not E2BSandbox.objects.filter(sandbox_id__startswith="old-").exists()
