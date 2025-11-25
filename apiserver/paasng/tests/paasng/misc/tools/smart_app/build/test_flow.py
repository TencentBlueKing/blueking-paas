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

import time

import pytest

from paasng.misc.tools.smart_app.build.flow import (
    SmartBuildCoordinator,
    SmartBuildStateMgr,
)
from paasng.misc.tools.smart_app.output import NullStream
from paasng.platform.engine.constants import JobStatus
from tests.paasng.misc.tools.smart_app.setup_utils import create_fake_smart_build

pytestmark = pytest.mark.django_db


class TestSmartBuildStateMgr:
    @pytest.fixture()
    def mgr(self, smart_build):
        """Create a SmartBuildStateMgr instance for testing"""
        return SmartBuildStateMgr(smart_build)

    def test_init(self, smart_build, mgr):
        """Test SmartBuildStateMgr initialization"""
        assert mgr.smart_build == smart_build
        assert mgr.stream is not None

    def test_from_smart_build_id(self, smart_build):
        """Test creating SmartBuildStateMgr from smart_build_id"""
        mgr = SmartBuildStateMgr.from_smart_build_id(str(smart_build.pk))
        assert mgr.smart_build.pk == smart_build.pk

    def test_update(self, smart_build, mgr):
        """Test updating smart_build fields"""
        mgr.update(status=JobStatus.SUCCESSFUL)
        smart_build.refresh_from_db()
        assert smart_build.status == JobStatus.SUCCESSFUL

    @pytest.mark.parametrize(
        ("status", "err_detail"),
        [
            (JobStatus.SUCCESSFUL, ""),
            (JobStatus.FAILED, "Build failed due to invalid configuration"),
            (JobStatus.INTERRUPTED, "Build was interrupted"),
        ],
    )
    def test_finish_with_various_statuses(self, smart_build, mgr, status, err_detail):
        """Test finishing with various statuses"""
        mgr.finish(status, err_detail=err_detail)
        smart_build.refresh_from_db()
        assert smart_build.status == status
        assert smart_build.err_detail == err_detail

    def test_finish_with_invalid_status(self, mgr):
        """Test finishing with invalid status raises ValueError"""
        with pytest.raises(ValueError, match="is not a valid finished status"):
            mgr.finish(JobStatus.PENDING)

    def test_finish_without_writing_to_stream(self, smart_build):
        """Test finishing without writing error to stream"""
        stream = NullStream()

        mgr = SmartBuildStateMgr(smart_build, stream=stream)
        mgr.finish(JobStatus.FAILED, err_detail="Error occurred")

        smart_build.refresh_from_db()
        assert smart_build.status == JobStatus.FAILED
        assert smart_build.err_detail == "Error occurred"

    @pytest.mark.parametrize(
        ("status", "should_stylize"),
        [
            (JobStatus.INTERRUPTED, True),
            (JobStatus.FAILED, True),
            (JobStatus.SUCCESSFUL, False),
        ],
    )
    def test_stylize_error(self, status, should_stylize):
        """Test error message stylization"""
        error_msg = "Test error message"
        styled = SmartBuildStateMgr._stylize_error(error_msg, status)

        if should_stylize:
            assert error_msg in styled
        else:
            assert styled == error_msg


class TestSmartBuildCoordinator:
    @pytest.fixture()
    def lock_key(self, smart_build):
        """Create a lock key for the smart build"""

        return f"{smart_build.operator}:{smart_build.app_code}"

    def test_normal(self, lock_key):
        coordinator = SmartBuildCoordinator(lock_key)
        assert coordinator.acquire_lock()
        assert not coordinator.acquire_lock()
        coordinator.release_lock()

        # Re-initialize a new object
        coordinator = SmartBuildCoordinator(lock_key)
        assert coordinator.acquire_lock()
        coordinator.release_lock()

    def test_lock_timeout(self, lock_key):
        coordinator = SmartBuildCoordinator(lock_key, timeout=0.1)
        assert coordinator.acquire_lock()
        assert not coordinator.acquire_lock()

        # wait for lock timeout
        time.sleep(0.2)
        assert coordinator.acquire_lock()
        coordinator.release_lock()

    def test_release_without_smart_build(self, smart_build, lock_key):
        coordinator = SmartBuildCoordinator(lock_key)
        coordinator.acquire_lock()
        coordinator.set_smart_build(smart_build)

        assert coordinator.get_current_smart_build() == smart_build
        coordinator.release_lock()
        assert coordinator.get_current_smart_build() is None

    def test_release_with_smart_build(self, smart_build, lock_key):
        coordinator = SmartBuildCoordinator(lock_key)
        coordinator.acquire_lock()
        coordinator.set_smart_build(smart_build)

        coordinator = SmartBuildCoordinator(lock_key)
        coordinator.release_lock(smart_build)
        assert coordinator.get_current_smart_build() is None

    def test_release_with_wrong_smart_build(self, smart_build, lock_key):
        coordinator = SmartBuildCoordinator(lock_key)
        coordinator.acquire_lock()
        coordinator.set_smart_build(smart_build)

        new_smart_build = create_fake_smart_build(
            package_name=smart_build.package_name,
            app_code=smart_build.app_code,
            operator=smart_build.operator,
        )
        coordinator = SmartBuildCoordinator(lock_key)
        with pytest.raises(ValueError, match=r"smart_build lock holder mismatch.*"):
            coordinator.release_lock(new_smart_build)

        assert coordinator.get_current_smart_build() == smart_build
        coordinator.release_lock(smart_build)
