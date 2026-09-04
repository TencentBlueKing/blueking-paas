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

"""Redis 跨进程协调原语。"""

from unittest.mock import MagicMock, patch

from paasng.utils.lock import acquire_once_per_period, redis_lock


class TestRedisLockBehavior:
    def test_lock_acquire_and_release(self):
        """测试锁的正常获取和释放"""
        mock_redis = MagicMock()
        mock_lock = MagicMock()
        # 正确模拟锁的获取结果和上下文管理器行为
        mock_lock.acquire.return_value = True
        mock_lock.__enter__.return_value = True
        mock_redis.lock.return_value = mock_lock

        with patch("paasng.utils.lock.get_default_redis", return_value=mock_redis):
            lock_key = "test:lock:key"
            with redis_lock(lock_key) as acquired:
                assert acquired is True
                mock_redis.lock.assert_called_once_with(
                    name=lock_key, timeout=300, blocking_timeout=0, thread_local=False
                )
            # 验证锁释放
            mock_lock.release.assert_called_once()

    def test_lock_not_acquired(self):
        """测试未能获取锁的情况"""
        mock_redis = MagicMock()
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = False
        mock_redis.lock.return_value = mock_lock

        with patch("paasng.utils.lock.get_default_redis", return_value=mock_redis):
            lock_key = "test:lock:key"
            with redis_lock(lock_key) as acquired:
                assert acquired is False


class TestAcquireOncePerPeriod:
    def test_first_caller_in_period_is_allowed(self):
        """测试周期内的第一次调用被放行"""
        mock_redis = MagicMock()
        mock_redis.set.return_value = True

        with patch("paasng.utils.lock.get_default_redis", return_value=mock_redis):
            key = "test:periodic:key"
            assert acquire_once_per_period(key, 300) is True
            # 必须是带 NX 与 EX 的单条命令，分成两步就不再是原子的
            mock_redis.set.assert_called_once_with(key, b"1", nx=True, ex=300)

    def test_later_callers_in_same_period_are_rejected(self):
        """测试同一周期内的后续调用被拒绝"""
        mock_redis = MagicMock()
        # redis-py 在 NX 未能写入时返回 None
        mock_redis.set.return_value = None

        with patch("paasng.utils.lock.get_default_redis", return_value=mock_redis):
            assert acquire_once_per_period("test:periodic:key", 300) is False
