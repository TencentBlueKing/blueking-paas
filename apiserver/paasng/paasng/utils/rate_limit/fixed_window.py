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

import redis
import wrapt
from rest_framework.response import Response
from rest_framework.status import HTTP_429_TOO_MANY_REQUESTS

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.utils.rate_limit.constants import UserAction


class RedisFixedWindowRateLimiter(abc.ABC):
    """基于 Redis 的固定窗口速率控制器"""

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

        固定窗口实现：
        +--------------+      +---------------------+      +------------------+  < threshold   +---------------------+
        | user request | ---> | calc current window | ---> | check used count | -------------> | increase used count |
        +--------------+      +---------------------+      +------------------+                +---------------------+
                                                                     |
                                                                     | >= threshold
                                                                     v
                                                           +----------------------+
                                                           | [✗] cause rate limit |
                                                           +----------------------+
        """
        cur_window = int(time.time() / self.window_size)
        key = self._gen_key(cur_window)
        count = self.redis_db.get(key)
        if not count:
            self.redis_db.set(key, 1, ex=self.window_size)
            return True

        if int(count) < self.threshold:
            self.redis_db.incr(key)
            return True

        return False

    @abc.abstractmethod
    def _gen_key(self, cur_window: int) -> str:
        """生成 redis 中的 key"""
        raise NotImplementedError


class UserActionRateLimiter(RedisFixedWindowRateLimiter):
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

    def _gen_key(self, cur_window: int) -> str:
        return f'bk_paas3:rate_limits:{self.username}:{self.action}:{cur_window}'


def rate_limits_by_user(action: UserAction, window_size: int, threshold: int):
    """适用于 Django View 方法的装饰器，提供频率限制的能力"""

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        rate_limiter = UserActionRateLimiter(
            get_default_redis(), instance.request.user.username, action, window_size, threshold
        )
        if not rate_limiter.is_allowed():
            return Response(status=HTTP_429_TOO_MANY_REQUESTS)

        return wrapped(*args, **kwargs)

    return wrapper
