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

from paas_wl.bk_app.applications.managers import update_metadata
from paas_wl.bk_app.deploy.actions.deploy import ObsoleteProcessesCleaner
from tests.paas_wl.utils.wl_app import create_wl_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestObsoleteProcessesCleaner:
    @pytest.mark.parametrize(
        ("prev_procfile", "curr_procfile", "expected_diff"),
        [
            # Unchanged proc lists
            ({"web": "command -x", "worker": "command -x"}, {"web": "command -x", "worker": "command -x"}, []),
            # Single proc that changes proc type
            ({"web": "command -x"}, {"worker": "command -x"}, [("web", True)]),
            # multiple procs that been replaced all
            (
                {"web": "command -x", "worker": "command -x"},
                {"new-web": "command -x", "new-worker": "command -x"},
                [("web", True), ("worker", True)],
            ),
            # Multiple procs that change command
            ({"web": "command -x", "worker": "command -x"}, {"web": "new-command -x", "worker": "new-command -x"}, []),
            # A mixed that has changed command, the proc that has different command should
            # has been ignored because mapper v2 does not depends on it when constructing
            # resource names.
            ({"web": "command -x", "worker": "command -x"}, {"web": "new_command -x"}, [("worker", True)]),
        ],
    )
    def test_find_all_latest_mapper_v2(self, wl_app, curr_procfile, prev_procfile, expected_diff):
        update_metadata(wl_app, mapper_version="v2")
        prev_release = create_wl_release(wl_app, release_params={"procfile": prev_procfile})
        curr_release = create_wl_release(
            wl_app,
            release_params={"version": prev_release.version + 1, "procfile": curr_procfile},
        )
        proc_cleaner = ObsoleteProcessesCleaner(curr_release, prev_release)
        self._assert_equal_find_all_results(proc_cleaner.find_all(), expected_diff)

    @pytest.mark.parametrize(
        ("prev_procfile", "curr_procfile", "expected_diff"),
        [
            # Single proc that changes proc type
            ({"web": "command -x"}, {"worker": "command -x"}, [("web", True)]),
            # A mixed that has changed command
            (
                {"web": "command -x", "worker": "command -x"},
                {"web": "new_command -x"},
                [("web", False), ("worker", True)],
            ),
            # Multiple procs that change command
            (
                {"web": "command -x", "worker": "command -x"},
                {"web": "new-command -x", "worker": "new-command -x"},
                [("web", False), ("worker", False)],
            ),
            # Multiple procs that change arguments only
            ({"web": "command -x", "worker": "command -x"}, {"web": "command -y", "worker": "command -y"}, []),
        ],
    )
    def test_find_all_latest_mapper_v1(self, wl_app, curr_procfile, prev_procfile, expected_diff):
        update_metadata(wl_app, mapper_version="v1")
        prev_release = create_wl_release(wl_app, release_params={"procfile": prev_procfile})
        curr_release = create_wl_release(
            wl_app,
            release_params={"version": prev_release.version + 1, "procfile": curr_procfile},
        )
        proc_cleaner = ObsoleteProcessesCleaner(curr_release, prev_release)
        self._assert_equal_find_all_results(proc_cleaner.find_all(), expected_diff)

    @staticmethod
    def _assert_equal_find_all_results(results, simplified_diff):
        """A helper function to compare find_all results."""
        sim_results = [(cfg.type, should_remove_svc) for cfg, should_remove_svc in results]
        sim_results.sort()
        assert sim_results == simplified_diff
