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

import pytest
import pytz

from paasng.pluginscenter.log.models import FieldFilter, count_filters_options, format_timestamp


@pytest.mark.parametrize(
    "value, input_format, expected",
    [
        (1000, "timestamp[s]", 1000),
        (1000, "timestamp[ns]", 1),
        (datetime.datetime(1970, 1, 1), "datetime", 0),
        (datetime.datetime(1970, 1, 1).replace(tzinfo=pytz.timezone("UTC")), "datetime", 0),
        (datetime.datetime(1970, 1, 1).replace(tzinfo=pytz.timezone("Asia/Shanghai")), "datetime", -29160),
    ],
)
def test_format_timestamp(value, input_format, expected):
    assert format_timestamp(value, input_format) == expected


@pytest.mark.parametrize(
    "logs, filters, expected",
    [
        # 测试忽略所有日志中不存在的字段
        (
            [
                {"log": "xxx"},
                {"log": "yyy"},
                {"log": "xxx"},
                {"log": "yyy"},
            ],
            {"log": FieldFilter(name="log", key="log.keyword"), "noise": FieldFilter(name="noise", key="noise")},
            [FieldFilter(name="log", key="log.keyword", options=[("xxx", "50.00%"), ("yyy", "50.00%")], total=4)],
        ),
        # 测试层级嵌套的日志和忽略未声明的字段
        (
            [
                {"nested": {"log": "x"}},
                {"nested": {"log": "y"}},
                {"nested": {"log": "y"}},
                {"nested": {"log": "x"}},
                {"nested": {"...": "..."}},
            ],
            {"nested.log": FieldFilter(name="nested.log", key="nested.log")},
            [FieldFilter(name="nested.log", key="nested.log", options=[("x", "50.00%"), ("y", "50.00%")], total=4)],
        ),
    ],
)
def test_count_filters_options(logs, filters, expected):
    assert count_filters_options(logs, filters) == expected
