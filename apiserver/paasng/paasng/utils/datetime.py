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

from __future__ import division

import datetime
import logging
import math

import arrow
import pytz
from django.utils import timezone

logger = logging.getLogger("root")


def get_time_delta(time_delta_string: str):
    """
    5m -> datetime.timedelta(minutes=5)
    5d -> datetime.timedelta(days=5)

    >>> get_time_delta(time_delta_string="5m") == datetime.timedelta(minutes=5)
    True
    >>> get_time_delta(time_delta_string="5d") == datetime.timedelta(days=5)
    True

    """
    count, _unit = time_delta_string[:-1], time_delta_string[-1]
    try:
        unit = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}[_unit]
    except KeyError:
        raise ValueError(f"{_unit} is not supported")

    return datetime.timedelta(**{unit: int(count)})


def calculate_interval(start_time, end_time, wide=False) -> str:
    """
    interval via the gap of query time
    fit for graph width >= 40%
    1  s  <-   60s
    10 s  <-   10m
    30 s  <-   30m
    1  m  <-   1h  - 60
    5  m  <-   6h  - 360
    10 m  <-   12h - 720
    30 m  <-   24h - 1440
    1  h  <-   72h - 4320
    3  h  <-   7d  - 10080
    12 h  <-   >7d
    """
    gap_seconds = (end_time - start_time) / 1000
    return calculate_gap_seconds_interval(gap_seconds, wide)


def calculate_gap_seconds_interval(gap_seconds, wide=False) -> str:
    gap_minutes = abs(math.ceil(gap_seconds / 60))
    if not wide:
        interval_options = ["1s", "10s", "30s", "1m", "5m", "10m", "30m", "1h", "3h", "1d"]
    else:
        interval_options = ["10s", "30s", "1m", "5m", "10m", "30m", "1h", "3h", "6h", "1d"]

    if gap_minutes <= 1:
        index = 0
    elif gap_minutes <= 10:
        index = 1
    elif gap_minutes <= 30:
        index = 2
    elif gap_minutes <= 60:
        index = 3
    elif gap_minutes <= 360:
        index = 4
    elif gap_minutes <= 720:
        index = 5
    elif gap_minutes <= 1440:
        index = 6
    elif gap_minutes <= 4320:
        index = 7
    elif gap_minutes <= 10080:
        index = 8
    else:
        index = 9
    return interval_options[index]


def trans_ts_to_local(ts):
    """
    to localtime
    """
    new_ts = None
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
        new_ts = datetime.datetime.strptime(ts, fmt)
        utc_ts = new_ts.replace(tzinfo=pytz.utc)

        current_tz = timezone.get_current_timezone()
        local_ts = utc_ts.astimezone(current_tz)

        return local_ts.strftime("%Y-%m-%d %H:%M:%S")
        #  new_ts = datetime.datetime.strptime(ts, fmt) + datetime.timedelta(hours=8)
        #  return new_ts.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        logger.exception("app_log, trans_ts_to_local fail!. [ts=%s]", ts)
    return new_ts


def time_to_epoch_millis(t, is_end=False):
    """
    utc datetime to epoch_millis
    """

    ts = (t - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()

    if is_end:
        # add 999 for more accuracy, like 23:59:59.999
        return int(ts * 1000) + 999
    else:
        return int(ts * 1000)

    #  s = int(time.mktime(t.timetuple()) * 1000)
    #  if is_end:
    #  s += 999
    #  return s


def strftime_ms(ms, fmt="%Y-%m-%d %H:%M:%S") -> str:
    """
    the timezone is local timezone
    """
    seconds = ms / 1000.0

    current_tz = timezone.get_current_timezone()
    dt = datetime.datetime.fromtimestamp(seconds, pytz.utc)
    local_dt = dt.astimezone(current_tz)

    return local_dt.strftime(fmt)


def convert_timestamp_to_str(timestamp: int, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """将整型的时间戳转化成要求的格式字符串"""
    return datetime.datetime.fromtimestamp(timestamp).strftime(fmt)


def valid_date_type(arg_date_str) -> datetime.date:
    """custom argparse type for user datetime values given from the command line"""
    try:
        return arrow.get(arg_date_str).date()
    except ValueError:
        msg = "Given Datetime ({0}) not valid! Expected format, 'YYYY-MM-DD'!".format(arg_date_str)
        raise ValueError(msg)
