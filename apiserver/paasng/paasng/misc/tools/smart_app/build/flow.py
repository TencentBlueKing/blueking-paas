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
from django.utils.translation import gettext_lazy as _

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.exceptions import SmartBuildShouldAbortError
from paasng.misc.tools.smart_app.models import SmartBuildPhase, SmartBuildRecord
from paasng.misc.tools.smart_app.models import SmartBuildStep as SmartBuildStepModel
from paasng.misc.tools.smart_app.output import SmartBuildStream, StreamType, get_default_stream
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.exceptions import HandleAppDescriptionError, StepNotInPresetListError
from paasng.platform.engine.utils.output import Style
from paasng.utils.error_message import find_coded_error_message

logger = logging.getLogger(__name__)


class SmartBuildProcedure:
    """Build step context managers"""

    TITLE_PREFIX: str = "正在"

    def __init__(
        self,
        stream: SmartBuildStream,
        smart_build: Optional[SmartBuildRecord],
        title: str,
        phase: SmartBuildPhase,
    ):
        self.stream = stream
        self.smart_build = smart_build
        self.phase = phase
        self.step_obj = self._get_step_obj(title)
        self.title = _(title)

    def __enter__(self):
        self.stream.write_title(f"{self.TITLE_PREFIX}{self.title}")
        if self.step_obj:
            self.step_obj.mark_and_write_to_stream(self.stream, JobStatus.PENDING)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if self.step_obj:
                self.step_obj.mark_and_write_to_stream(self.stream, JobStatus.SUCCESSFUL)
            return False

        is_known_exc = exc_type in [SmartBuildShouldAbortError, HandleAppDescriptionError]
        if is_known_exc:
            msg = _("步骤 [{title}] 出错了，原因：{reason}。").format(
                title=Style.Title(self.title), reason=Style.Warning(exc_val)
            )
        else:
            msg = _("步骤 [{title}] 出错了，请稍候重试。").format(title=Style.Title(self.title))

        if coded_message := find_coded_error_message(exc_val):
            msg += coded_message

        if not is_known_exc:
            logger.exception(msg)

        self.stream.write_message(msg, StreamType.STDERR)
        if self.step_obj:
            self.step_obj.mark_and_write_to_stream(self.stream, JobStatus.FAILED)
        return False

    def _get_step_obj(self, title: str) -> Optional["SmartBuildStepModel"]:
        if not self.smart_build:
            return None
        try:
            return self.phase.get_step_by_name(title)
        except StepNotInPresetListError as e:
            logger.info("%s, skip", e.message)
            return None


class SmartBuildStateMgr:
    """Build state manager"""

    def __init__(
        self, smart_build: SmartBuildRecord, phase_type: SmartBuildPhaseType, stream: Optional[SmartBuildStream] = None
    ):
        self.smart_build = smart_build
        self.stream = stream or get_default_stream(smart_build)
        self.phase_type = phase_type
        self.coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")

    @classmethod
    def from_smart_build_id(cls, smart_build_id: str, phase_type: "SmartBuildPhaseType"):
        smart_build = SmartBuildRecord.objects.get(pk=smart_build_id)
        return cls(smart_build, phase_type)

    def update(self, **fields):
        return self.smart_build.update_fields(**fields)

    def finish(self, status: JobStatus, err_detail: str = "", write_to_stream: bool = True):
        """Finish a s-mart build process"""
        if status not in JobStatus.get_finished_states():
            raise ValueError(f"{status} is not a valid finished status")
        if write_to_stream and err_detail:
            self.stream.write_message(self._stylize_error(err_detail, status), stream=StreamType.STDERR)
        self.update(status=status, err_detail=err_detail)

        self.coordinator.release_lock(expected_smart_build=self.smart_build)

    @staticmethod
    def _stylize_error(error_detail: str, status: JobStatus) -> str:
        """Format error messages"""
        if status == JobStatus.INTERRUPTED:
            return Style.Warning(error_detail)
        if status == JobStatus.FAILED:
            return Style.Error(error_detail)
        return error_detail


class SmartBuildCoordinator:
    """Build coordinator: manage build status and prevent duplicate builds"""

    DEFAULT_LOCK_TIMEOUT = 15 * 60
    DEFAULT_TOKEN = "None"
    POLLING_TIMEOUT = 90

    def __init__(
        self,
        composed_key: str,
        timeout: Optional[float] = None,
        redis_db: Optional[redis.Redis] = None,
    ):
        self.redis = redis_db or get_default_redis()
        self.key_name_lock = f"smart_build_lock:{composed_key}:lock"
        self.key_name_build = f"smart_build_lock:{composed_key}:build"
        self.key_name_latest_polling_time = f"smart_build_lock:{composed_key}:latest_polling_time"
        self.timeout_ms = int((timeout or self.DEFAULT_LOCK_TIMEOUT) * 1000)

    def acquire_lock(self) -> bool:
        """Acquire build lock"""
        return bool(self.redis.set(self.key_name_lock, self.DEFAULT_TOKEN, nx=True, px=self.timeout_ms))

    def release_lock(self, expected_smart_build: Optional[SmartBuildRecord] = None):
        """Release build lock"""

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
                self.release_lock(expected_smart_build)
            except ValueError as e:
                logger.warning("Failed to release the build lock: %s", e)

    def set_smart_build(self, smart_build: SmartBuildRecord):
        """Set current s-mart build"""
        self.redis.set(self.key_name_build, str(smart_build.pk), px=self.timeout_ms)
        self.update_polling_time()

    def get_current_smart_build(self) -> Optional[SmartBuildRecord]:
        """Get current s-mart build"""
        if build_id := self.redis.get(self.key_name_build):
            return SmartBuildRecord.objects.get(pk=force_str(build_id))
        return None

    def update_polling_time(self):
        """Update status polling time"""
        self.redis.set(self.key_name_latest_polling_time, time.time(), px=self.timeout_ms)

    @property
    def is_status_polling_timeout(self) -> bool:
        """Check if status polling timed out"""
        if not (latest_polling_time := self.redis.get(self.key_name_latest_polling_time)):
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
