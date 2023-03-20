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
import datetime
from typing import Optional, Tuple, Union

from paasng.utils.datetime import calculate_gap_seconds_interval, calculate_interval


def get_time_delta(time_delta_string) -> datetime.timedelta:
    """
    5m -> datetime.timedelta(minutes=5)
    5d -> datetime.timedelta(days=5)
    """
    count, _unit = time_delta_string[:-1], time_delta_string[-1]
    try:
        unit = {
            "s": "seconds",
            "m": "minutes",
            "h": "hours",
            "d": "days",
            "w": "weeks",
        }[_unit]
    except KeyError:
        raise ValueError(f"{_unit} is not supported")

    return datetime.timedelta(**{unit: int(count)})


DEFAULT_EPOCH = datetime.datetime(1970, 1, 1)


def get_epoch_milliseconds(dt: datetime.datetime) -> int:
    """Return total number of milliseconds.


    This total number of milliseconds is the elapsed milliseconds since timestamp or unix epoch
    counting from 1 January 1970.
    """
    EPOCH = DEFAULT_EPOCH
    if dt.tzinfo is not None:
        # respect tzinfo, if given
        EPOCH = datetime.datetime(1970, 1, 1, tzinfo=dt.tzinfo)
    timestamp = (dt - EPOCH).total_seconds()
    return int(timestamp * 1000)


class SmartTimeRange:
    """
    A tool class for LogClient, transfer time_range[start_time, end_time] to ES format
    """

    def __init__(
        self,
        time_range: str,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
    ):
        self.time_range = time_range

        if self.time_range == "customized":
            if start_time is None or end_time is None:
                raise ValueError("start_time & end_time is necessary if time_range is customized")
        else:
            end_time = datetime.datetime.now()
            start_time = end_time - get_time_delta(self.time_range)

        self.start_time = start_time
        self.end_time = end_time

    @property
    def is_absolute(self):
        return self.time_range == "customized"

    @staticmethod
    def _get_epoch_millis(dt: datetime.datetime, is_end=False) -> int:
        # time to epoch millis
        milliseconds = get_epoch_milliseconds(dt)
        if is_end:
            # add 999 for more accuracy, like 23:59:59.999
            milliseconds += 999
        return milliseconds

    def get_head_and_tail(self, all_epoch_millis=False) -> Union[Tuple[str, str], Tuple[int, int]]:
        if self.is_absolute or all_epoch_millis:
            return (
                self._get_epoch_millis(self.start_time),
                self._get_epoch_millis(self.end_time, is_end=True),
            )
        else:
            return f"now-{self.time_range}", "now"

    def get_time_range_filter(self, field_name: str):
        start_time, end_time = self.get_head_and_tail()
        time_range_filter = {field_name: {"gte": start_time, "lte": end_time}}
        if self.is_absolute:
            time_range_filter[field_name]["format"] = "epoch_millis"
        return time_range_filter

    def detect_date_histogram_interval(self):
        """Detect the best interval be used in aggregate date histogram"""
        if self.is_absolute:
            # currently, use narrow interval,
            # if the design of apm UI make each graph width > 40% then use wide interval
            start_time, end_time = self.get_head_and_tail()
            return calculate_interval(start_time, end_time)
        else:
            # NOTE: replace `seconds` with `total_seconds`
            return calculate_gap_seconds_interval(get_time_delta(self.time_range).total_seconds())
