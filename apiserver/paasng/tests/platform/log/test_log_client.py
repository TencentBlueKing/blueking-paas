# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import pytest

from paasng.platform.log.client import SmartTimeRange


class TestSmartTimeRange:
    @pytest.mark.parametrize(
        "time_range,start,end,interval",
        [
            ("5m", "now-5m", "now", "10s"),
            ("1h", "now-1h", "now", "1m"),
            ("3h", "now-3h", "now", "5m"),
            ("12h", "now-12h", "now", "10m"),
            ("1d", "now-1d", "now", "30m"),
            ("7d", "now-7d", "now", "3h"),
        ],
    )
    def test_range_time(self, time_range, start, end, interval):
        smart_time_range = SmartTimeRange(time_range=time_range)
        start_time, end_time = smart_time_range.get_head_and_tail()
        assert start_time == start
        assert end_time == end
        assert smart_time_range.get_interval() == interval
        assert smart_time_range.get_time_range_filter() == {"@timestamp": {"gte": start, "lte": end}}

    @pytest.mark.parametrize(
        "start_time,end_time,start_stamp,end_stamp,interval",
        [
            ("2019-02-11 00:00:00", "2019-02-12 00:00:00", 1549814400000, 1549900800999, "1h"),
        ],
    )
    def test_absolute_time(self, start_time, end_time, start_stamp, end_stamp, interval):
        with pytest.raises(ValueError):
            SmartTimeRange(time_range="customized")

        smart_time_range = SmartTimeRange(time_range="customized", start_time=start_time, end_time=end_time)
        start_time_stamp, end_time_stamp = smart_time_range.get_head_and_tail()
        assert start_time_stamp == start_stamp
        assert end_time_stamp == end_stamp
        assert smart_time_range.get_interval() == interval
        assert smart_time_range.get_time_range_filter() == {
            "@timestamp": {"gte": start_stamp, "lte": end_stamp, "format": "epoch_millis"}
        }
