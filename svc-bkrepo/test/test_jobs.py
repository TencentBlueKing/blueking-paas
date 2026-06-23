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

from unittest.mock import MagicMock, patch

import pytest
from svc_bk_repo.vendor.jobs import _try_auto_expand

_1MB = 2**20
_1GB = 2**30
_10GB = 10 * _1GB


def _stat(repo_name="private-repo", max_size=_1GB, used=900 * _1MB, auto_expand=None, quota_used_rate=None):
    """构造 RepoQuotaStatistics mock"""
    stat = MagicMock()
    stat.repo_name = repo_name
    stat.max_size = max_size
    stat.used = used
    if quota_used_rate is not None:
        stat.quota_used_rate = quota_used_rate
    elif max_size is None:
        stat.quota_used_rate = 0
    else:
        stat.quota_used_rate = used / max_size * 100

    inst = MagicMock()
    inst.get_credentials.return_value = {"private_bucket": "private-repo"}
    inst.config = auto_expand or {}
    stat.instance = inst
    return stat


class TestTryAutoExpand:
    """_try_auto_expand 单元测试"""

    @patch("svc_bk_repo.vendor.jobs.extend_quota")
    @pytest.mark.parametrize(
        "stat",
        [
            pytest.param(_stat(), id="no-config"),
            pytest.param(
                _stat(auto_expand={"auto_expand": {"private": {"enabled": False, "threshold": 80}}}),
                id="disabled",
            ),
            pytest.param(
                _stat(
                    max_size=_1GB,
                    used=700 * _1MB,
                    auto_expand={"auto_expand": {"private": {"enabled": True, "threshold": 80}}},
                ),
                id="usage-below-threshold",
            ),
            pytest.param(
                _stat(
                    repo_name="public-repo",
                    max_size=None,
                    auto_expand={"auto_expand": {"public": {"enabled": True, "threshold": 80}}},
                    quota_used_rate=90,
                ),
                id="max-size-is-none",
            ),
            pytest.param(
                _stat(
                    max_size=_10GB,
                    auto_expand={"auto_expand": {"private": {"enabled": True, "threshold": 80}}},
                ),
                id="already-at-max-allowed",
            ),
        ],
    )
    def test_early_return(self, mock_extend, stat):
        """已满足 early-return 条件时不应调用 extend_quota"""
        _try_auto_expand(stat, MagicMock())
        mock_extend.assert_not_called()

    @patch("svc_bk_repo.vendor.jobs.extend_quota")
    def test_success(self, mock_extend):
        """扩容成功时应更新 stat 的 max_size 并 save"""
        old_size = _1GB
        new_size = old_size + _1GB
        mock_extend.return_value = new_size

        stat = _stat(
            max_size=old_size,
            auto_expand={"auto_expand": {"private": {"enabled": True, "threshold": 85}}},
        )
        _try_auto_expand(stat, MagicMock())

        mock_extend.assert_called_once()
        assert stat.max_size == new_size
        assert stat.save.called
