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

import logging
import time
from contextlib import contextmanager
from typing import Optional

import redis
from django.utils.encoding import force_str

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.misc.tools.build_smart.models import SmartBuildRecord

logger = logging.getLogger(__name__)


class SmartBuildCoordinator:
    """Coordinate the tasks of building s-smart packages

    Including managing build status and preventing duplicate builds
    """

    # The lock will be released anyway after {DEFAULT_LOCK_TIMEOUT} seconds
    DEFAULT_LOCK_TIMEOUT = 15 * 60
    # A placeholder value for lock
    DEFAULT_TOKEN = "None"
    # If not any poll in 90s, assume the poller is failed
    POLLING_TIMEOUT = 90

    def __init__(
        self,
        signature: str,
        timeout: Optional[float] = None,
        redis_db: Optional[redis.Redis] = None,
    ):
        self.redis = redis_db or get_default_redis()

        self.key_name_lock = f"smart_build_lock:{signature}:lock"
        self.key_name_build = f"smart_build_lock:{signature}:build"
        self.key_name_interrupted = f"smart_build_lock:{signature}:interrupted"
        self.key_name_latest_polling_time = f"smart_build_lock:{signature}:latest_polling_time"
        # use milliseconds
        self.timeout_ms = int((timeout or self.DEFAULT_LOCK_TIMEOUT) * 1000)

    def acquire_lock(self) -> bool:
        """Acquire lock to start a new s-mart build"""
        if self.redis.set(self.key_name_lock, self.DEFAULT_TOKEN, nx=True, px=self.timeout_ms):  # noqa: SIM103
            return True
        return False

    def release_lock(self, expected_smart_build: Optional[SmartBuildRecord] = None):
        """Finish a s-mart build process, release the s-mart build lock

        :param expected_smart_build: if given, will raise ValueError when the ongoing build is
            not identical with given build
        :raises: ValueError when build not matched
        """

        def execute_release(pipe):
            if expected_smart_build:
                build_id = pipe.get(self.key_name_build)
                if build_id and (force_str(build_id) != str(expected_smart_build.pk)):
                    raise ValueError(
                        f"build lock holder mismatch, found: {build_id}, expected: {expected_smart_build.pk}"
                    )
            pipe.delete(self.key_name_lock)
            # Clean build key
            pipe.delete(self.key_name_build)
            # Clean user interruptions
            pipe.delete(self.key_name_interrupted)
            # Clean latest polling time key
            pipe.delete(self.key_name_latest_polling_time)

        self.redis.transaction(execute_release, self.key_name_build)

    def release_if_polling_timed_out(self, expected_smart_build: SmartBuildRecord):
        """release the build lock if status polling time out of the s-mart build"""
        if (
            (current_build_record := self.get_current_smart_build())
            and self.is_status_polling_timeout
            and current_build_record.pk == expected_smart_build.pk
        ):
            # Release build lock
            try:
                self.release_lock(expected_smart_build=expected_smart_build)
            except ValueError as e:
                logger.warning("Failed to release the build lock: %s", e)

    def set_smart_build(self, smart_build: SmartBuildRecord):
        """Set current s-mart build"""
        self.redis.set(self.key_name_build, str(smart_build.pk), px=self.timeout_ms)
        self.update_polling_time()

    def get_current_smart_build(self) -> Optional[SmartBuildRecord]:
        """Get current s-mart build"""
        build_id = self.redis.get(self.key_name_build)
        if build_id:
            return SmartBuildRecord.objects.get(pk=force_str(build_id))
        return None

    def set_interrupted(self, ts: float):
        """Set interrupted flag"""
        if ts is None:
            ts = time.time()
        self.redis.set(self.key_name_interrupted, ts, px=self.timeout_ms)

    def get_interrupted_time(self) -> Optional[float]:
        """Get interrupted time"""
        ts = self.redis.get(self.key_name_interrupted)
        return ts

    def update_polling_time(self):
        """Storage status reporting time"""
        self.redis.set(self.key_name_latest_polling_time, time.time(), px=self.timeout_ms)

    @property
    def is_status_polling_timeout(self) -> bool:
        """Check if the reporting time has timed out

        Currently used for controlling build and hook processes
        """
        latest_polling_time = self.redis.get(self.key_name_latest_polling_time)
        # If there is no last report status time, it is considered not timed out,
        # and the query time is set to the last report time
        if not latest_polling_time:
            self.update_polling_time()
            return False

        return (time.time() - float(force_str(latest_polling_time))) > self.POLLING_TIMEOUT

    @contextmanager
    def release_on_error(self):
        try:
            yield
        except Exception:
            self.release_lock()
            raise
