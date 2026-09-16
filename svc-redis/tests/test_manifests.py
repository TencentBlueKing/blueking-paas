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
from svc_redis.controller.entities import RedisPlanConfig
from svc_redis.controller.manifests import get_redis_resource
from svc_redis.controller.resource_presets import resolve_plan_resources


def _plan_config(**overrides) -> RedisPlanConfig:
    data = {"type": "Redis", "redis_version": "v7.0.15", "cluster_name": "test-cluster"}
    data.update(overrides)
    return RedisPlanConfig(**data)


class TestResolvePlanResources:
    def test_explicit_requests_and_limits(self):
        resolved = resolve_plan_resources(
            _plan_config(
                resources={
                    "requests": {"cpu": "500m", "memory": "1Gi", "hugepages-2Mi": "1Gi"},
                    "limits": {"cpu": "2", "memory": "2Gi", "hugepages-2Mi": "1Gi"},
                }
            )
        )
        assert resolved.requests == {"cpu": "500m", "memory": "1Gi", "hugepages-2Mi": "1Gi"}
        assert resolved.limits == {"cpu": "2", "memory": "2Gi", "hugepages-2Mi": "1Gi"}

    def test_preset_with_explicit_overlay(self):
        resolved = resolve_plan_resources(_plan_config(resources={"preset": "medium", "limits": {"cpu": "2"}}))
        assert resolved.requests == {"cpu": "500m", "memory": "1024Mi", "ephemeral-storage": "50Mi"}
        assert resolved.limits == {"cpu": "2", "memory": "1536Mi", "ephemeral-storage": "2Gi"}

    def test_explicit_requests_only_copies_to_limits(self):
        resolved = resolve_plan_resources(_plan_config(resources={"requests": {"cpu": "500m", "memory": "1Gi"}}))
        assert resolved.requests == {"cpu": "500m", "memory": "1Gi"}
        assert resolved.limits == {"cpu": "500m", "memory": "1Gi"}

    def test_legacy_memory_size_2gi(self):
        resolved = resolve_plan_resources(_plan_config(memory_size="2Gi"))
        assert resolved.requests == {"cpu": "500m", "memory": "1Gi"}
        assert resolved.limits == {"cpu": "1000m", "memory": "2Gi"}

    def test_resources_wins_over_memory_size(self):
        resolved = resolve_plan_resources(_plan_config(memory_size="4Gi", resources={"preset": "small"}))
        assert resolved.requests == {"cpu": "500m", "memory": "512Mi", "ephemeral-storage": "50Mi"}
        assert resolved.limits == {"cpu": "750m", "memory": "768Mi", "ephemeral-storage": "2Gi"}


class TestGetRedisResource:
    def test_get_standalone_redis_manifest_with_default_resources(self):
        deployable = get_redis_resource(_plan_config()).to_deployable()

        assert deployable["spec"]["kubernetesConfig"]["service"]["additional"]["enabled"] is False
        resources = deployable["spec"]["kubernetesConfig"]["resources"]
        assert resources["requests"] == {"cpu": "250m", "memory": "256Mi", "ephemeral-storage": "50Mi"}
        assert resources["limits"] == {"cpu": "375m", "memory": "384Mi", "ephemeral-storage": "2Gi"}

    # Expected quotas come from Bitnami, not the implementation's RESOURCE_PRESETS.
    @pytest.mark.parametrize(
        ("preset", "requests_cpu", "requests_memory", "limits_cpu", "limits_memory"),
        [
            ("nano", "100m", "128Mi", "150m", "192Mi"),
            ("micro", "250m", "256Mi", "375m", "384Mi"),
            ("small", "500m", "512Mi", "750m", "768Mi"),
            ("medium", "500m", "1024Mi", "750m", "1536Mi"),
            ("large", "1.0", "2048Mi", "1.5", "3072Mi"),
            ("xlarge", "1.0", "3072Mi", "3.0", "6144Mi"),
            ("2xlarge", "1.0", "3072Mi", "6.0", "12288Mi"),
        ],
    )
    def test_get_replication_redis_manifest(self, preset, requests_cpu, requests_memory, limits_cpu, limits_memory):
        plan_config = _plan_config(type="RedisReplication", resources={"preset": preset})
        deployable = get_redis_resource(plan_config).to_deployable()

        assert "service" not in deployable["spec"]["kubernetesConfig"]
        resources = deployable["spec"]["kubernetesConfig"]["resources"]
        assert resources == {
            "requests": {"cpu": requests_cpu, "memory": requests_memory, "ephemeral-storage": "50Mi"},
            "limits": {"cpu": limits_cpu, "memory": limits_memory, "ephemeral-storage": "2Gi"},
        }
