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

import base64
import calendar
import datetime
import re

# URL path variables
PVAR_REGION = "(?P<region>[a-z0-9_-]{1,32})"
PVAR_NAME = "(?P<name>[a-z0-9_-]{1,64})"
PVAR_CLUSTER_NAME = "(?P<name>[a-z0-9_-]{1,64})"

# This pattern is widely used by kubernetes
DNS_SAFE_PATTERN = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"

# RFC3339Nano regex pattern, such as "2023-10-01T12:34:56.123456789Z" or "2023-10-01T12:34:56.123456789+08:00"
RFC3339_NANO_REGEX = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d{9})([Zz]|[+-]\d{2}:\d{2})$")


def rfc3339nano_to_unix_timestamp(value: str) -> int:
    """Convert RFC3339Nano format to Unix timestamp in nanoseconds"""

    match = RFC3339_NANO_REGEX.match(value)
    if not match:
        raise ValueError("Invalid RFC3339Nano format")

    base_time_str = match.group(1)
    fraction_str = match.group(2)
    tz_str = match.group(3)

    # 解析时间和时区
    dt = datetime.datetime.strptime(base_time_str, "%Y-%m-%dT%H:%M:%S")
    if tz_str.upper() != "Z":
        # parse the timezone offset
        sign = -1 if tz_str.startswith("-") else 1
        hour_str, minute_str = tz_str[1:].split(":")
        hours, minutes = int(hour_str), int(minute_str)
        tz_offset = datetime.timedelta(hours=hours, minutes=minutes)
        dt = dt - sign * tz_offset
    timestamp_seconds = calendar.timegm(dt.timetuple())

    # 解析纳秒部分
    nano_str = fraction_str[1:]
    nanoseconds = int(nano_str)

    return timestamp_seconds * 1_000_000_000 + nanoseconds


def b64encode(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def b64decode(text: str) -> str:
    return base64.b64decode(text.encode()).decode()
