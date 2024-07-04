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

from datetime import timedelta

import pytest

from paasng.utils.datetime import get_time_delta, humanize_timedelta


@pytest.mark.parametrize(
    ("input", "expected_output"),
    [
        ("5s", timedelta(seconds=5)),
        ("12d", timedelta(days=12)),
    ],
)
def test_get_time_delta(input, expected_output):
    assert get_time_delta(input) == expected_output


@pytest.mark.parametrize(
    ("delta", "expected_output"),
    [
        (timedelta(days=5, hours=2, minutes=30, seconds=15), "5d2h30m15s"),
        (timedelta(days=0, hours=8, minutes=45, seconds=32), "8h45m32s"),
        (timedelta(days=0, hours=0, minutes=25, seconds=9), "25m9s"),
        (timedelta(seconds=5), "5s"),
        (timedelta(days=1, seconds=1), "1d0h0m1s"),
        (timedelta(hours=1, seconds=0), "1h0m0s"),
        (timedelta(days=0), "0s"),
        (timedelta(hours=0), "0s"),
        (timedelta(seconds=0), "0s"),
    ],
)
def test_humanize_timedelta(delta, expected_output):
    assert humanize_timedelta(delta) == expected_output
