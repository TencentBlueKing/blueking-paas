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
import pytest

from paasng.utils.datetime import calculate_gap_seconds_interval


class TestUtil:
    @pytest.mark.parametrize(
        "seconds,wide,expected",
        [
            (10, False, "1s"),
            (10, True, "10s"),
            (10800, False, "5m"),
            (10800, True, "10m"),
            (604900, False, "1d"),
            (-604900, True, "1d"),
        ],
    )
    def test_calculate_gap_seconds_interval(self, seconds, wide, expected):
        assert calculate_gap_seconds_interval(seconds, wide) == expected
