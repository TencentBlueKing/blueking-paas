# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
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
        self.key = self._gen_key()

        raw = self.redis_db.get(self.key)
        self.records = msgpack.unpackb(raw) if raw else []

        if len(self.records) < self.threshold:
            self._update_bucket(cur_timestamp)
            return True

        if cur_timestamp - self.records[-1] >= self.window_size:
            self._update_bucket(cur_timestamp, pop=True)
            return True

        return False

    @abc.abstractmethod
    def _gen_key(self) -> str:
        """生成 redis 中的 key"""
        raise NotImplementedError

    def _update_bucket(self, cur_timestamp: int, pop: bool = False):
        """更新令牌桶数据，若指定 pop 为 True，则会移除最老的时间戳"""
        self.records.insert(0, cur_timestamp)
        if pop:
            self.records.pop()
        self.redis_db.set(self.key, msgpack.packb(self.records), ex=self.window_size)


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
        return f'bk_paas3:rate_limits:{self.username}:{self.action}'
