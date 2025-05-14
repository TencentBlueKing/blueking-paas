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
from django.core.exceptions import ObjectDoesNotExist
from svc_redis.cluster.exceptions import ResourceNotEnoughError
from svc_redis.cluster.models import Cluster, TencentCLBListener


@pytest.mark.django_db
class TestTencentCLBListenerManager:
    @pytest.fixture
    def cluster(self):
        return Cluster.objects.create(name="test-cluster")

    @pytest.fixture
    def clb_listener(self, cluster):
        return TencentCLBListener.objects.create(
            name="test-clb", cluster=cluster, clb_id="clb-123456", vip="192.168.1.1", port=6379, is_allocated=False
        )

    def test_acquire_by_cluster_name(self, cluster, clb_listener):
        """测试成功获取未分配的CLB监听器"""
        acquired = TencentCLBListener.objects.acquire_by_cluster_name(cluster.name)

        assert acquired.is_allocated is True

    def test_acquire_by_cluster_name_no_available(self, cluster):
        """测试没有可用监听器时抛出异常"""
        with pytest.raises(ResourceNotEnoughError):
            TencentCLBListener.objects.acquire_by_cluster_name(cluster.name)

    def test_release_success(self, cluster, clb_listener):
        """测试成功释放监听器"""
        clb_listener.is_allocated = True
        clb_listener.save()

        TencentCLBListener.objects.release(cluster_name=cluster.name, vip=clb_listener.vip, port=clb_listener.port)

        clb_listener.refresh_from_db()
        assert clb_listener.is_allocated is False

    def test_release_already_released(self, cluster, clb_listener):
        """测试释放未分配的监听器"""

        TencentCLBListener.objects.release(cluster_name=cluster.name, vip=clb_listener.vip, port=clb_listener.port)

        assert clb_listener.is_allocated is False

    def test_release_non_existent(self, cluster):
        """测试释放不存在的监听器"""
        with pytest.raises(ObjectDoesNotExist):
            TencentCLBListener.objects.release(cluster_name=cluster.name, vip="1.1.1.1", port=9999)
