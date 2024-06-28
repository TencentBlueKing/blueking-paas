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

import abc
import time

import msgpack
import redis

from paasng.utils.rate_limit.constants import UserAction


class RedisTokenBucketRateLimiter(abc.ABC):
    """基于 Redis 的令牌桶速率控制器"""

    def __init__(self, redis_db: redis.Redis, window_size: int, threshold: int):
        """
        :param redis_db: redis client
        :param window_size: 时间窗口长度（单位：秒）
        :param threshold: 时间窗口内的次数阈值
        """
        self.redis_db = redis_db
        self.window_size = window_size
        self.threshold = threshold

    def is_allowed(self) -> bool:
        """
        是否允许当前行为（未受速率限制影响）

        令牌桶实现：
        +------------------------------------------+
        |               user request               |
        +------------------------------------------+
                           |
                           |
                           v
        +------------------------------------------+    < threshold     +------------------------------+
        |           check queue length             | -----------------> | [✓] lpush current timestamp  |
        +------------------------------------------+                    +------------------------------+
                           |
                           | >= threshold
                           v
        +------------------------------------------+   < window_size    +----------------------+
        |   check timedelta (current and oldest)   | -----------------> | [✗] cause rate limit |
        +------------------------------------------+                    +----------------------+
                           |
                           | >= window_size
                           v
        +------------------------------------------+
        |   [✓] rpop and lpush current timestamp   |
        +------------------------------------------+
        """
        cur_timestamp = int(time.time())
        key = self._gen_key()

        raw = self.redis_db.get(key)
        records = msgpack.unpackb(raw) if raw else []

        if len(records) < self.threshold:
            records.insert(0, cur_timestamp)
            self.redis_db.set(key, msgpack.packb(records), ex=self.window_size)
            return True

        while cur_timestamp - records[-1] >= self.window_size:
            records.pop(-1)

        if len(records) < self.threshold:
            records.insert(0, cur_timestamp)
            self.redis_db.set(key, msgpack.packb(records), ex=self.window_size)
            return True

        return False

    @abc.abstractmethod
    def _gen_key(self) -> str:
        """生成 redis 中的 key"""
        raise NotImplementedError


class UserActionRateLimiter(RedisTokenBucketRateLimiter):
    """针对用户行为的速率控制器"""

    def __init__(
        self,
        redis_db: redis.Redis,
        username: str,
        action: UserAction,
        window_size: int,
        threshold: int,
    ):
        """
        :param redis_db: redis client
        :param username: 用户 ID
        :param action: 用户操作名
        :param window_size: 时间窗口长度（单位：秒）
        :param threshold: 时间窗口内的次数阈值
        """
        super().__init__(redis_db, window_size, threshold)
        self.username = username
        self.action = action

    def _gen_key(self) -> str:
        return f"bk_paas3:rate_limits:{self.username}:{self.action}"
