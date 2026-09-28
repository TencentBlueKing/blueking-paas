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

from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from paasng.infras.iam.v4.registry import AggregatedSyncResult, ModelSyncResult, SyncItem


def _aggregated(**counts_and_items) -> AggregatedSyncResult:
    result = ModelSyncResult(system_id="bk_paas3", **counts_and_items)
    return AggregatedSyncResult(results=[result])


class TestSyncIAMV4ModelCommand:
    @pytest.fixture(autouse=True)
    def _setup_iam_v4_env(self, settings):
        """命令只在 V4 且未配置跳过时执行同步"""
        settings.BK_IAM_VERSION = "v4"
        settings.BK_IAM_SKIP = False

    @pytest.mark.parametrize(
        ("version", "skip", "expected_msg"),
        [
            ("v3", False, "BK_IAM_VERSION=v3"),
            ("v4", True, "BK_IAM_SKIP"),
        ],
    )
    def test_skipped(self, settings, version, skip, expected_msg):
        settings.BK_IAM_VERSION = version
        settings.BK_IAM_SKIP = skip
        stdout = StringIO()

        with mock.patch(
            "paasng.infras.iam.members.management.commands.sync_iam_v4_model.sync_iam_v4_models",
        ) as mocked:
            call_command("sync_iam_v4_model", stdout=stdout)

        mocked.assert_not_called()
        assert expected_msg in stdout.getvalue()

    def test_prints_counts_on_success(self):
        aggregated = _aggregated(
            created=[SyncItem(kind="action", identifier="view_basic_info", system_id="bk_paas3")],
        )
        stdout = StringIO()

        with mock.patch(
            "paasng.infras.iam.members.management.commands.sync_iam_v4_model.sync_iam_v4_models",
            return_value=aggregated,
        ):
            call_command("sync_iam_v4_model", stdout=stdout)

        output = stdout.getvalue()
        assert "新增=1" in output
        assert "更新=0" in output
        assert "删除=0" in output
        assert "告警=0" in output
        assert "失败=0" in output
        assert "view_basic_info" in output

    def test_exits_nonzero_and_prints_request_id_on_failure(self):
        aggregated = _aggregated(
            created=[SyncItem(kind="action", identifier="view_basic_info", system_id="bk_paas3")],
            failures=[
                SyncItem(
                    kind="action",
                    identifier="edit_basic_info",
                    system_id="bk_paas3",
                    detail="create action failed",
                    request_id="req-fail",
                )
            ],
        )
        stdout = StringIO()

        with (
            mock.patch(
                "paasng.infras.iam.members.management.commands.sync_iam_v4_model.sync_iam_v4_models",
                return_value=aggregated,
            ),
            pytest.raises(CommandError, match="失败=1"),
        ):
            call_command("sync_iam_v4_model", stdout=stdout)

        output = stdout.getvalue()
        assert "edit_basic_info" in output
        assert "req-fail" in output
        assert "view_basic_info" in output

    def test_dry_run_flag_is_forwarded(self):
        aggregated = _aggregated()
        stdout = StringIO()

        with mock.patch(
            "paasng.infras.iam.members.management.commands.sync_iam_v4_model.sync_iam_v4_models",
            return_value=aggregated,
        ) as mocked:
            call_command("sync_iam_v4_model", "--dry-run", stdout=stdout)

        assert mocked.call_args.kwargs["dry_run"] is True
        assert mocked.call_args.kwargs["prune"] is False
        assert "[dry-run]" in stdout.getvalue()

    def test_prune_flag_is_forwarded(self):
        aggregated = _aggregated(
            deleted=[SyncItem(kind="action", identifier="obsolete_action", system_id="bk_paas3")],
        )
        stdout = StringIO()

        with mock.patch(
            "paasng.infras.iam.members.management.commands.sync_iam_v4_model.sync_iam_v4_models",
            return_value=aggregated,
        ) as mocked:
            call_command("sync_iam_v4_model", "--prune", stdout=stdout)

        assert mocked.call_args.kwargs["prune"] is True
        assert mocked.call_args.kwargs["dry_run"] is False
        output = stdout.getvalue()
        assert "删除=1" in output
        assert "obsolete_action" in output
