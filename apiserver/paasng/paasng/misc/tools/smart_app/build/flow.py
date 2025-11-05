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

import redis
from django.utils import timezone
from django.utils.encoding import force_str

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from paasng.misc.tools.smart_app.output import (
    SmartBuildStream,
    StreamType,
    get_default_stream,
    make_channel_stream,
)
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.utils.output import Style

logger = logging.getLogger(__name__)


class SmartBuildStateMgr:
    """s-mart build state manager"""

    def __init__(
        self,
        smart_build: SmartBuildRecord,
        stream: SmartBuildStream | None = None,
    ):
        self.smart_build = smart_build
        self.stream = stream or get_default_stream(smart_build)
        self.coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")

    @classmethod
    def from_smart_build_id(cls, smart_build_id: str, stream: SmartBuildStream | None = None):
        record = SmartBuildRecord.objects.get(pk=smart_build_id)
        stream = stream or make_channel_stream(record)
        return cls(record, stream)

    def update(self, **fields):
        return self.smart_build.update_fields(**fields)

    def start(self):
        """Start a s-mart build process"""
        start_time = timezone.now()
        self.stream.write_event(
            "Builder Process",
            {
                "status": JobStatus.PENDING,
                "start_time": timezone.localtime(start_time).isoformat(),
            },
        )
        self.update(status=JobStatus.PENDING.value, start_time=start_time)

    def finish(self, status: JobStatus, err_detail: str = ""):
        """Finish a s-mart build process

        :param status: the final status of smart build
        :param err_detail: only useful when status is "FAILED"
        """

        if status not in JobStatus.get_finished_states():
            raise ValueError(f"{status} is not a valid finished status")

        if err_detail:
            self.stream.write_message(self._stylize_error(err_detail, status), stream=StreamType.STDERR)

        start_time, end_time = self.smart_build.start_time, timezone.now()
        self.stream.write_event(
            "Builder Process",
            {
                "status": status,
                "start_time": timezone.localtime(start_time).isoformat(),
                "end_time": timezone.localtime(end_time).isoformat(),
            },
        )
        self.update(status=status, end_time=end_time, err_detail=err_detail)

    @staticmethod
    def _stylize_error(error_detail: str, status: JobStatus) -> str:
        """Format error messages"""

        if status == JobStatus.INTERRUPTED:
            return Style.Warning(error_detail)
        elif status == JobStatus.FAILED:
            return Style.Error(error_detail)
        else:
            return error_detail


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
        composed_key: str,
        timeout: float | None = None,
        redis_db: redis.Redis | None = None,
    ):
        self.redis = redis_db or get_default_redis()
        self.key_name_lock = f"smart_build_lock:{composed_key}:lock"
        self.key_name_build = f"smart_build_lock:{composed_key}:build"
        self.key_name_latest_polling_time = f"smart_build_lock:{composed_key}:latest_polling_time"
        # use milliseconds
        self.timeout_ms = int((timeout or self.DEFAULT_LOCK_TIMEOUT) * 1000)

    def acquire_lock(self):
        """Acquire build lock"""

        if self.redis.set(self.key_name_lock, self.DEFAULT_TOKEN, nx=True, px=self.timeout_ms):  # noqa: SIM103
            return True
        return False

    def release_lock(self, expected_smart_build: SmartBuildRecord | None = None):
        """Finish a s-mart build process, release the s-mart build lock

        :param expected_smart_build: if given, will raise ValueError when the ongoing build is
            not identical with given build
        :raises: ValueError when build not matched
        """

        def execute_release(pipe):
            if expected_smart_build:
                smart_build_id = pipe.get(self.key_name_build)
                if smart_build_id and (force_str(smart_build_id) != str(expected_smart_build.pk)):
                    raise ValueError(
                        f"smart_build lock holder mismatch, found: {smart_build_id}, expected: {expected_smart_build.pk}"
                    )
            pipe.delete(self.key_name_lock, self.key_name_build, self.key_name_latest_polling_time)

        self.redis.transaction(execute_release, self.key_name_build)

    def release_if_polling_timed_out(self, expected_smart_build: SmartBuildRecord):
        """Release lock if status polling timed out"""

        if (
            (current_build_record := self.get_current_smart_build())
            and self.is_status_polling_timeout
            and current_build_record.pk == expected_smart_build.pk
        ):
            try:
                # Release build lock
                self.release_lock(expected_smart_build=expected_smart_build)
            except ValueError as e:
                logger.warning("Failed to release the build lock: %s", e)

    def set_smart_build(self, smart_build: SmartBuildRecord):
        """Set current s-mart build"""

        self.redis.set(self.key_name_build, str(smart_build.pk), px=self.timeout_ms)
        self.update_polling_time()

    def get_current_smart_build(self):
        """Get current s-mart build"""

        build_id = self.redis.get(self.key_name_build)
        if build_id:
            return SmartBuildRecord.objects.get(pk=force_str(build_id))
        return None

    def update_polling_time(self):
        """Update status polling time"""

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
