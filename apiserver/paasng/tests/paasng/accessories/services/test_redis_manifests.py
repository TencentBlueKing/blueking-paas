# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

from paasng.accessories.services.providers.redis.manifests import (
    get_external_clb_service_manifest,
    get_redis_password_secret_manifest,
    get_redis_resource,
    get_service_monitor_manifest,
)
from paasng.accessories.services.providers.redis.schemas import RedisInstanceConfig, RedisPlanConfig

pytestmark = pytest.mark.django_db


class TestRedisManifest:
    @pytest.fixture()
    def instance_config(self):
        return RedisInstanceConfig(
            cluster_name="test_cluster",
            clb_id="clb-test",
            host="127.0.0.1",
            port="6800",
            password="test_password",
        )

    @pytest.fixture()
    def plan_config(self):
        return RedisPlanConfig(
            kind="RedisReplication",
            redis_version="v7.0.12",
            persistent_storage=True,
            monitor=True,
            memory_size="4Gi",
        )

    def test_external_clb_service_manifest(self, plan_config, instance_config):
        manifest = get_external_clb_service_manifest(plan_config, instance_config)
        print(manifest)

    def test_redis_password_secret_manifest(self):
        manifest = get_service_monitor_manifest()
        print(manifest)

    def test_service_monitor_manifest(self, instance_config):
        manifest = get_redis_password_secret_manifest(instance_config.password)
        print(manifest)

    def test_redis_resource(self, plan_config, instance_config):
        manifest = get_redis_resource(plan_config).to_deployable()
        print(manifest)
