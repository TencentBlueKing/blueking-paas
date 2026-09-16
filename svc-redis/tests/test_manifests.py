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
from pydantic import ValidationError
from svc_redis.controller.entities import RedisPlanConfig
from svc_redis.controller.manifests import (
    DisableAdditionalServiceConstructor,
    ResourceManifestConstructor,
    create_redis_base_resource,
    get_redis_resource,
)
from svc_redis.controller.resource_presets import RESOURCE_PRESETS, resolve_plan_resources
from svc_redis.vendor.redis_crd.constants import RedisType


def _plan_config(**overrides) -> RedisPlanConfig:
    data = {"type": "Redis", "redis_version": "v7.0.15", "cluster_name": "test-cluster"}
    data.update(overrides)
    return RedisPlanConfig(**data)


def _apply_resources(plan_config: RedisPlanConfig):
    res = create_redis_base_resource(plan_config.type, "test-redis")
    ResourceManifestConstructor().apply_to(res, plan_config)
    return res.spec.kubernetesConfig.resources


class TestDisableAdditionalServiceConstructor:
    def test_standalone_redis_disables_additional_service(self):
        res = create_redis_base_resource(RedisType.REDIS.value, "test-redis")
        DisableAdditionalServiceConstructor().apply_to(res, _plan_config())

        assert res.spec.kubernetesConfig.service.additional.enabled is False
        deployable = res.to_deployable()
        assert deployable["spec"]["kubernetesConfig"]["service"]["additional"]["enabled"] is False

    def test_replication_redis_does_not_set_service(self):
        plan_config = _plan_config(type="RedisReplication")
        res = create_redis_base_resource(RedisType.REDIS_REPLICATION.value, "test-redis")
        DisableAdditionalServiceConstructor().apply_to(res, plan_config)

        assert res.spec.kubernetesConfig.service is None
        assert "service" not in res.to_deployable()["spec"]["kubernetesConfig"]


class TestResolvePlanResources:
    def test_default_uses_micro_preset(self):
        resolved = resolve_plan_resources(_plan_config())
        assert resolved.requests == RESOURCE_PRESETS["micro"]["requests"]
        assert resolved.limits == RESOURCE_PRESETS["micro"]["limits"]

    def test_preset_medium(self):
        resolved = resolve_plan_resources(_plan_config(resources={"preset": "medium"}))
        assert resolved.requests == {"cpu": "500m", "memory": "1Gi"}
        assert resolved.limits == {"cpu": "500m", "memory": "1Gi"}

    @pytest.mark.parametrize("preset", list(RESOURCE_PRESETS))
    def test_all_presets_resolve(self, preset):
        resolved = resolve_plan_resources(_plan_config(resources={"preset": preset}))
        assert resolved.requests == RESOURCE_PRESETS[preset]["requests"]
        assert resolved.limits == RESOURCE_PRESETS[preset]["limits"]

    def test_unknown_preset_is_rejected(self):
        with pytest.raises(ValidationError):
            _plan_config(resources={"preset": "huge"})

    def test_explicit_requests_and_limits(self):
        resolved = resolve_plan_resources(
            _plan_config(
                resources={
                    "requests": {"cpu": "500m", "memory": "1Gi"},
                    "limits": {"cpu": "2", "memory": "2Gi"},
                }
            )
        )
        assert resolved.requests == {"cpu": "500m", "memory": "1Gi"}
        assert resolved.limits == {"cpu": "2", "memory": "2Gi"}

    def test_preset_with_explicit_overlay(self):
        resolved = resolve_plan_resources(_plan_config(resources={"preset": "medium", "limits": {"cpu": "2"}}))
        assert resolved.requests == {"cpu": "500m", "memory": "1Gi"}
        assert resolved.limits == {"cpu": "2", "memory": "1Gi"}

    def test_explicit_requests_only_copies_to_limits(self):
        resolved = resolve_plan_resources(_plan_config(resources={"requests": {"cpu": "500m", "memory": "1Gi"}}))
        assert resolved.requests == {"cpu": "500m", "memory": "1Gi"}
        assert resolved.limits == {"cpu": "500m", "memory": "1Gi"}

    def test_extra_resource_keys_passthrough(self):
        resolved = resolve_plan_resources(
            _plan_config(
                resources={
                    "requests": {"cpu": "500m", "memory": "1Gi", "hugepages-2Mi": "1Gi"},
                    "limits": {"cpu": "2", "memory": "2Gi", "hugepages-2Mi": "1Gi"},
                }
            )
        )
        assert resolved.requests["hugepages-2Mi"] == "1Gi"
        assert resolved.limits["hugepages-2Mi"] == "1Gi"

    def test_legacy_memory_size_2gi_uses_default_preset(self):
        resolved = resolve_plan_resources(_plan_config(memory_size="2Gi"))
        assert resolved.requests == RESOURCE_PRESETS["micro"]["requests"]
        assert resolved.limits == RESOURCE_PRESETS["micro"]["limits"]

    def test_legacy_memory_size_4gi(self):
        resolved = resolve_plan_resources(_plan_config(memory_size="4Gi"))
        assert resolved.requests == {"cpu": "1000m", "memory": "2Gi"}
        assert resolved.limits == {"cpu": "2000m", "memory": "4Gi"}

    def test_resources_wins_over_memory_size(self):
        resolved = resolve_plan_resources(_plan_config(memory_size="4Gi", resources={"preset": "small"}))
        assert resolved.requests == RESOURCE_PRESETS["small"]["requests"]
        assert resolved.limits == RESOURCE_PRESETS["small"]["limits"]


class TestResourceManifestConstructor:
    def test_preset_written_to_manifest(self):
        resources = _apply_resources(_plan_config(resources={"preset": "medium"}))
        assert resources.requests == {"cpu": "500m", "memory": "1Gi"}
        assert resources.limits == {"cpu": "500m", "memory": "1Gi"}


class TestGetRedisResource:
    def test_get_standalone_redis_manifest(self):
        deployable = get_redis_resource(_plan_config(resources={"preset": "micro"})).to_deployable()

        assert deployable["spec"]["kubernetesConfig"]["service"]["additional"]["enabled"] is False
        resources = deployable["spec"]["kubernetesConfig"]["resources"]
        assert resources["requests"] == {"cpu": "250m", "memory": "256Mi"}
        assert resources["limits"] == {"cpu": "250m", "memory": "256Mi"}

    def test_get_replication_redis_manifest(self):
        plan_config = _plan_config(type="RedisReplication", resources={"preset": "medium"})
        deployable = get_redis_resource(plan_config).to_deployable()

        assert "service" not in deployable["spec"]["kubernetesConfig"]
        resources = deployable["spec"]["kubernetesConfig"]["resources"]
        assert resources["requests"] == {"cpu": "500m", "memory": "1Gi"}
        assert resources["limits"] == {"cpu": "500m", "memory": "1Gi"}
