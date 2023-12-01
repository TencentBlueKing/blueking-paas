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
import arrow
import pytest

from paasng.utils.es_log.misc import filter_indexes_by_time_range
from paasng.utils.es_log.time_range import SmartTimeRange


@pytest.fixture()
def indexes():
    return [
        "k8s_app_log_-2022.10.10",
        "k8s_app_log_-2022.10.11",
        "k8s_app_log_-2023.05.11",
        "k8s_app_log_-2023.05.22",
    ] + ["k8s_app_log_-2023.5.23" + "k8s_app_log-2o23.05.24"]


@pytest.mark.parametrize(
    ("time_range", "expected"),
    [
        (
            SmartTimeRange(
                time_range="customized",
                start_time=arrow.get("2021-10-05").datetime,
                end_time=arrow.get("2021-10-11").datetime,
            ),
            [],
        ),
        (
            SmartTimeRange(
                time_range="customized",
                start_time=arrow.get("2022-10-05").datetime,
                end_time=arrow.get("2022-10-11").datetime,
            ),
            ["k8s_app_log_-2022.10.10", "k8s_app_log_-2022.10.11"],
        ),
        (
            SmartTimeRange(
                time_range="customized",
                start_time=arrow.get("2022-10-05").datetime,
                end_time=arrow.get("2022-10-10").datetime,
            ),
            ["k8s_app_log_-2022.10.10"],
        ),
        (
            SmartTimeRange(
                time_range="customized",
                start_time=arrow.get("2022-10-05").datetime,
                end_time=arrow.get("2023-05-10").datetime,
            ),
            ["k8s_app_log_-2022.10.10", "k8s_app_log_-2022.10.11"],
        ),
        (
            SmartTimeRange(
                time_range="customized",
                start_time=arrow.get("2022-10-05").datetime,
                end_time=arrow.get("2023-05-21").datetime,
            ),
            ["k8s_app_log_-2022.10.10", "k8s_app_log_-2022.10.11", "k8s_app_log_-2023.05.11"],
        ),
        (
            SmartTimeRange(
                time_range="customized",
                start_time=arrow.get("2022-10-11 02:00:00+00:00").datetime,
                end_time=arrow.get("2022-10-11 03:00:00+00:00").datetime,
            ),
            ["k8s_app_log_-2022.10.11"],
        ),
        (
            SmartTimeRange(
                time_range="customized",
                start_time=arrow.get("2022-10-11 02:00:00+03:00").datetime,
                end_time=arrow.get("2022-10-11 03:00:00+00:00").datetime,
            ),
            ["k8s_app_log_-2022.10.10", "k8s_app_log_-2022.10.11"],
        ),
    ],
)
def test_filter_indexes_by_time_range(indexes, time_range, expected):
    assert filter_indexes_by_time_range(indexes, time_range) == expected
