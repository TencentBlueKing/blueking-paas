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

"""monitor 采集主流程的测试"""

import json
import time
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils.timezone import now
from paas_service.models import Plan, Service, ServiceInstance, ServiceInstanceConfig
from svc_redis.monitor import exporter, instances, k8s
from svc_redis.monitor.collector import RedisInstanceMetricsCollector
from svc_redis.monitor.entities import RedisInstance, RedisInstanceStatus
from svc_redis.monitor.exporter import ExporterUsage

pytestmark = pytest.mark.django_db


class _Obj(dict):
    """kres 的动态资源对象: 必需字段用属性访问, 可选字段用下标访问且缺失为 None"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__.update(self)

    def __missing__(self, key):
        return None


def _instance(app_info=None) -> ServiceInstance:
    """建一个已分配实例: 套餐开启 monitor, 命名空间 ns-a"""
    service = Service.objects.create(name="redis", category=1)
    plan = Plan.objects.create(
        name="redis",
        service=service,
        config=json.dumps({"cluster_name": "redis-cluster", "memory_size": "2Gi", "monitor": True}),
    )
    instance = ServiceInstance.objects.create(plan=plan, config={"namespace": "ns-a"})
    ServiceInstanceConfig.objects.create(instance=instance, paas_app_info=app_info or {})
    return instance


def _statefulset(replicas=1, ready_replicas=1):
    return _Obj(metadata=_Obj(name=k8s.INSTANCE_NAME), status=_Obj(replicas=replicas, readyReplicas=ready_replicas))


def _pod(exporter=True, oom_finished_at=None):
    containers = [_Obj(name="redis")] + ([_Obj(name="redis-exporter")] if exporter else [])
    terminated = {"reason": "OOMKilled", "finishedAt": oom_finished_at.isoformat()} if oom_finished_at else None
    return _Obj(
        metadata=_Obj(name="svc-redis-0", labels=_Obj({"redis-role": "master"})),
        spec=_Obj(containers=containers),
        status=_Obj(containerStatuses=[_Obj(state=_Obj(), lastState=_Obj(terminated=terminated))]),
    )


def _samples() -> list:
    """跑一次完整采集, 返回全部指标样本"""
    return [sample for family in RedisInstanceMetricsCollector().collect() for sample in family.samples]


def _metrics() -> dict[tuple[str, str], float]:
    """(指标名, 实例 ID) -> 值; 自监控指标没有实例 ID"""
    return {(s.name, s.labels.get("bk_instance", "")): s.value for s in _samples()}


@pytest.fixture(autouse=True)
def _cluster_client(monkeypatch):
    """测试环境里没有真集群, 换成占位对象"""
    monkeypatch.setattr(instances, "get_client_by_cluster_name", lambda name: object())


def test_metrics_of_instance(monkeypatch):
    """正常实例: 五个指标一次出全, 标签来自实例身份与平台应用信息, 内存分母回退套餐上限"""
    iid = str(_instance(app_info={"app_code": "app", "module": "default", "environment": "stag"}).uuid)
    monkeypatch.setattr(k8s, "list_statefulsets", lambda *args: {"ns-a": [_statefulset()]})
    monkeypatch.setattr(k8s, "list_pods", lambda *args: {"ns-a": [_pod()]})
    monkeypatch.setattr(
        exporter,
        "fetch_usage",
        lambda *args: ExporterUsage(used_memory=1024, maxmemory=0, connected_clients=10, maxclients=100),
    )

    alive = next(s for s in _samples() if s.name == "redis_instance_alive")

    assert alive.labels == {
        "bk_instance": iid,
        "bk_cluster": "redis-cluster",
        "namespace": "ns-a",
        "bk_app_code": "app",
        "bk_module": "default",
        "bk_env": "stag",
    }
    assert _metrics() == {
        ("redis_instance_alive", iid): 1.0,
        ("redis_instance_memory_usage_rate", iid): 1024 / (2 * 1024**3),
        ("redis_instance_connection_usage_rate", iid): 0.1,
        ("redis_instance_oom_killed", iid): 0.0,
        ("redis_instance_exporter_up", iid): 1.0,
        ("redis_instance_collect_instances", ""): 1.0,
        ("redis_instance_collect_success", ""): 1.0,
    }


@pytest.mark.parametrize(
    ("age", "expected"), [(settings.METRIC_OOM_KILLED_WINDOW // 2, 1.0), (settings.METRIC_OOM_KILLED_WINDOW + 60, 0.0)]
)
def test_oom_killed(monkeypatch, age, expected):
    """OOM 只统计最近 METRIC_OOM_KILLED_WINDOW 秒内发生的"""
    iid = str(_instance().uuid)
    monkeypatch.setattr(k8s, "list_statefulsets", lambda *args: {})
    monkeypatch.setattr(
        k8s, "list_pods", lambda *args: {"ns-a": [_pod(oom_finished_at=now() - timedelta(seconds=age))]}
    )

    assert _metrics()[("redis_instance_oom_killed", iid)] == expected


def test_not_alive(monkeypatch):
    """副本没全部就绪时判为不可用"""
    iid = str(_instance().uuid)
    monkeypatch.setattr(k8s, "list_statefulsets", lambda *args: {"ns-a": [_statefulset(replicas=3, ready_replicas=2)]})
    monkeypatch.setattr(k8s, "list_pods", lambda *args: {})

    assert _metrics()[("redis_instance_alive", iid)] == 0.0


def test_metrics_missing_when_no_exporter(monkeypatch):
    """实例没有 exporter sidecar: 只出存活与 OOM"""
    iid = str(_instance().uuid)
    monkeypatch.setattr(k8s, "list_statefulsets", lambda *args: {"ns-a": [_statefulset()]})
    monkeypatch.setattr(k8s, "list_pods", lambda *args: {"ns-a": [_pod(exporter=False)]})

    assert _metrics() == {
        ("redis_instance_alive", iid): 1.0,
        ("redis_instance_oom_killed", iid): 0.0,
        ("redis_instance_collect_instances", ""): 1.0,
        ("redis_instance_collect_success", ""): 1.0,
    }


def test_exporter_up_zero_when_fetch_failed(monkeypatch):
    """实例有 exporter 但取数失败: exporter_up=0, 使用率缺失"""
    iid = str(_instance().uuid)
    monkeypatch.setattr(k8s, "list_statefulsets", lambda *args: {})
    monkeypatch.setattr(k8s, "list_pods", lambda *args: {"ns-a": [_pod()]})
    monkeypatch.setattr(exporter, "fetch_usage", lambda *args: None)

    assert _metrics() == {
        ("redis_instance_oom_killed", iid): 0.0,
        ("redis_instance_exporter_up", iid): 0.0,
        ("redis_instance_collect_instances", ""): 1.0,
        ("redis_instance_collect_success", ""): 1.0,
    }


def test_single_cluster_failure_is_isolated(monkeypatch):
    """一个集群查询失败只影响该集群实例, 其它集群照常回填"""
    ok = RedisInstanceStatus(RedisInstance("i-ok", "c-ok", "ns-a", "app", "mod", "stag"))
    bad = RedisInstanceStatus(RedisInstance("i-bad", "c-bad", "ns-b", "app", "mod", "stag"))
    monkeypatch.setattr(instances, "get_client_by_cluster_name", lambda name: object())
    monkeypatch.setattr(k8s, "list_statefulsets", lambda client, ns, deadline: {"ns-a": [_statefulset()]})
    monkeypatch.setattr(k8s, "list_pods", lambda client, ns, deadline: {"ns-a": [_pod()]})
    # 让 c-bad 的命名空间查询失败
    monkeypatch.setattr(
        k8s,
        "list_statefulsets",
        lambda client, ns, deadline: (
            (_ for _ in ()).throw(RuntimeError("down")) if "ns-b" in ns else {"ns-a": [_statefulset()]}
        ),
    )

    instances._fill_k8s_states([ok, bad], time.monotonic() + 5)

    assert ok.alive is True
    assert bad.alive is None  # 该集群失败, 字段保持缺失
