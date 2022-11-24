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
import logging
import time
import typing
from datetime import timedelta

from django_redis.client import DefaultClient

if typing.TYPE_CHECKING:
    from redis.client import StrictRedis

logger = logging.getLogger(__name__)


class TwemRedis:
    KEYS = "twem::cache::keys::set"
    forever = float("+inf")
    insert_key_commands = (
        "hset",
        "zadd",
        "sadd",
        "lpush",
        "lpushx",
        "rpush",
        "rpushx",
        "lset",
        "linsert",
        "getset",
        "incrby",
        "incr",
        "incrbyfloat",
        "setnx",
    )

    insert_mapping_commands = (
        "mset",
        "msetnx",
    )

    insert_ex_key_commands = (
        "psetex",
        "setex",
    )

    def __init__(self, client: 'StrictRedis'):
        self._client = client

        for m in self.insert_key_commands:
            setattr(self, m, self._execute_insert(getattr(client, m)))

        for m in self.insert_mapping_commands:
            setattr(self, m, self._execute_insert_mapping(getattr(client, m)))

        for m in self.insert_ex_key_commands:
            setattr(self, m, self._execute_insert_ex(getattr(client, m)))

    def __getattr__(self, item):
        return getattr(self._client, item)

    def _execute_insert(self, fn):
        def wrapper(name, *args, **options):
            result = fn(name, *args, **options)
            if result:
                self._add_keys(name)
            return result

        return wrapper

    def _execute_insert_ex(self, fn):
        def wrapper(name, ex, *args, **options):
            result = fn(name, ex, *args, **options)
            if result:
                self._add_keys(name, ex=ex.total_seconds() if isinstance(ex, timedelta) else ex)
            return result

        return wrapper

    def _execute_insert_mapping(self, fn):
        def wrapper(mapping, *args, **options):
            result = fn(mapping, *args, **options)
            if result:
                self._add_keys(*mapping.keys())
            return result

        return wrapper

    def _add_keys(self, *name, ex: 'float' = None):
        expires = self.forever
        # 总是比 redis 久一点以避免误差
        if ex:
            expires = time.time() + ex
        self._client.zadd(self.KEYS, {i: expires for i in name})

    def set(self, name, value, ex=None, px=None, nx=False, xx=False):
        result = self._client.set(name, value, ex, px, nx, xx)
        if result:
            self._add_keys(name, ex=px / 1000 if px else ex or None)
        return result

    def delete(self, *names):
        result = self._client.delete(*names)
        if result > 0:
            self._client.zrem(self.KEYS, *names)
        return result

    def expire(self, name, ttl):
        result = self._client.expire(name, ttl)
        if result:
            self._client.zadd(self.KEYS, {name: time.time() + ttl})
        return result

    def persist(self, name):
        result = self._client.persist(name)
        if result:
            self._client.zadd(self.KEYS, {name: self.forever})
        return result

    def house_keeping(self):
        """clean cached keys"""
        client = self._client
        deletes = []
        updates = {}
        for k, ts in client.zscan_iter(self.KEYS, "*"):
            ttl = client.ttl(k)
            if ttl == -2:  # 不存在
                deletes.append(k)
            elif ttl == -1:
                if ts != self.forever:
                    updates[k] = self.forever
            elif ttl == 0:
                deletes = k
            else:
                updates[k] = time.time() + ttl

        if updates:
            client.zadd(self.KEYS, updates)

        if deletes:
            client.zrem(self.KEYS, *deletes)

    def flushdb(self, asynchronous=False):
        self.delete(*self.keys(), self.KEYS)

    def flushall(self, asynchronous=False):
        self.delete(*self.keys(), self.KEYS)

    def pipeline(self, transaction=True, shard_hint=None):
        return self

    def execute(self, raise_on_error=True):
        return []

    def scan_iter(self, match=None, count=None):
        now = time.time()
        client = self._client
        for k, ts in client.zscan_iter(self.KEYS, match):
            if ts <= now:
                # 理论上过期
                ttl = client.ttl(k)
                if ttl == -2 or ttl == 0:  # 已删除
                    client.zrem(self.KEYS, k)
                    continue
                else:  # 已更新未同步
                    client.zadd(self.KEYS, {k: self.forever if ttl == -1 else time.time() + ttl})

            if count is not None:
                count -= 1
            yield k

            if count == 0:
                break

    def keys(self, pattern='*'):
        return list(self.scan_iter(pattern, None))


class Client(DefaultClient):
    def get_client(self, write=True, tried=(), show_index=False):
        parts = super().get_client(write, tried, show_index)
        if show_index:
            return TwemRedis(parts[0]), parts[1]
        return TwemRedis(parts)

    def _update(self, key, delta=0, version=None, client: 'StrictRedis' = None):
        client = client or self.get_client()
        key = self.make_key(key, version=version)
        if not client.exists(key):
            raise ValueError(f"Key '{key}' not found")
        return client.incr(key, delta)

    def incr(self, key, delta=1, version=None, client=None, ignore_key_check=False):
        return self._update(key, delta, version, client)

    def decr(self, key, delta=1, version=None, client=None):
        return self._update(key, -delta, version, client)
