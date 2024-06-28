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

import datetime

import arrow
import pytest

from paasng.utils.es_log.time_range import SmartTimeRange, get_epoch_milliseconds


@pytest.mark.parametrize(
    ("dt", "ignore_timezone", "expected"),
    [
        (datetime.datetime(2023, 4, 20, 15, 40, 51, 997557), True, 1682005251997),
        (datetime.datetime(2023, 4, 20, 15, 40, 51, 997557), False, 1682005251997),
        (
            datetime.datetime(2023, 4, 20, 15, 40, 51, 997557, tzinfo=datetime.timezone(datetime.timedelta(hours=1))),
            True,
            1682005251997,
        ),
        (
            datetime.datetime(2023, 4, 20, 15, 40, 51, 997557, tzinfo=datetime.timezone(datetime.timedelta(hours=1))),
            False,
            # Note: 这个时间不一样的
            1682005251997 - 3600 * 1000,
        ),
        (
            datetime.datetime(2023, 4, 20, 15, 40, 51, 997557, tzinfo=datetime.timezone(datetime.timedelta(hours=-1))),
            True,
            1682005251997,
        ),
        (
            datetime.datetime(2023, 4, 20, 15, 40, 51, 997557, tzinfo=datetime.timezone(datetime.timedelta(hours=-1))),
            False,
            # Note: 这个时间不一样的
            1682005251997 + 3600 * 1000,
        ),
    ],
)
def test_get_epoch_milliseconds(dt, ignore_timezone, expected):
    assert get_epoch_milliseconds(dt, ignore_timezone) == expected


class TestSmartTimeRange:
    @pytest.mark.parametrize(
        ("time_range", "expected_start", "expected_end"),
        [
            ("5m", "now-5m", "now"),
            ("1h", "now-1h", "now"),
            ("3h", "now-3h", "now"),
            ("12h", "now-12h", "now"),
            ("1d", "now-1d", "now"),
            ("7d", "now-7d", "now"),
        ],
    )
    def test_relative_time(self, time_range, expected_start, expected_end):
        smart_time_range = SmartTimeRange(time_range=time_range)
        start_time, end_time = smart_time_range.get_head_and_tail()
        assert start_time == expected_start
        assert end_time == expected_end
        assert smart_time_range.get_time_range_filter("@timestamp") == {
            "@timestamp": {"gte": expected_start, "lte": expected_end}
        }

    @pytest.mark.parametrize(
        ("start_time", "end_time", "expected_start", "expected_end"),
        [
            # datetime without timezone
            (
                datetime.datetime.utcfromtimestamp(1549814400),
                datetime.datetime.utcfromtimestamp(1549900800),
                1549814400000,
                1549900800999,
            ),
            (
                datetime.datetime.fromtimestamp(1549814400),
                datetime.datetime.fromtimestamp(1549900800),
                1549843200000,
                1549929600999,
            ),
            # datetime with timezone
            # 测试结果和时区无关, 只和日期的字面值相关
            (
                arrow.get(datetime.datetime(2019, 2, 11)).datetime,
                arrow.get(datetime.datetime(2019, 2, 12)).datetime,
                1549843200000,
                1549929600999,
            ),
            (
                arrow.get(datetime.datetime(2019, 2, 11), "Asia/Shanghai").datetime,
                arrow.get(datetime.datetime(2019, 2, 12), "Asia/Shanghai").datetime,
                1549814400000,
                1549900800999,
            ),
            # arrow.get(1549814400) -> datetime.daatetime(2019, 02, 10, 16)
            # arrow.get(1549900800) -> datetime.daatetime(2019, 02, 11, 16)
            (
                arrow.get(1549814400).datetime,
                arrow.get(1549900800).datetime,
                1549814400000,
                1549900800999,
            ),
            (
                arrow.get(1549814400).replace(tzinfo="Asia/Shanghai").datetime,
                arrow.get(1549900800).replace(tzinfo="Asia/Shanghai").datetime,
                1549785600000,
                1549872000999,
            ),
        ],
    )
    def test_absolute_time(self, start_time, end_time, expected_start, expected_end):
        with pytest.raises(ValueError, match=r".*is necessary if time_range is customized"):
            SmartTimeRange(time_range="customized")

        smart_time_range = SmartTimeRange(time_range="customized", start_time=start_time, end_time=end_time)
        start_time_stamp, end_time_stamp = smart_time_range.get_head_and_tail()
        assert start_time_stamp == expected_start
        assert end_time_stamp == expected_end
        assert smart_time_range.get_time_range_filter("@timestamp") == {
            "@timestamp": {"gte": expected_start, "lte": expected_end, "format": "epoch_millis"}
        }
