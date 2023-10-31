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
import atexit
from datetime import datetime
from functools import partial
from pathlib import Path

import pytest
from filelock import FileLock

from paasng.infras.bkmonitorv3.params import QueryAlarmStrategiesParams, QueryAlertsParams
from tests.utils.helpers import generate_random_string

fn = Path(__file__).parent / ".random"
with FileLock(str(fn.absolute()) + ".lock"):
    if fn.is_file():
        SEARCH_KEYWORD, FAKE_APP_CODE = (
            fn.read_text()
            .strip()
            .split(
                "|",
            )
        )
    else:
        SEARCH_KEYWORD = generate_random_string(6)
        FAKE_APP_CODE = generate_random_string(6)
        fn.write_text("|".join([SEARCH_KEYWORD, FAKE_APP_CODE]))


@atexit.register
def clear_filelock():
    fn.unlink(missing_ok=True)


AppQueryAlertsParams = partial(
    QueryAlertsParams, app_code=FAKE_APP_CODE, start_time=datetime.now(), end_time=datetime.now()
)

AppQueryAlarmStrategiesParams = partial(QueryAlarmStrategiesParams, app_code=FAKE_APP_CODE)


class TestQueryAlertsParams:
    @pytest.mark.parametrize(
        'query_params, expected_query_string',
        [
            (
                AppQueryAlertsParams(),
                f'labels:(PAAS_BUILTIN AND {FAKE_APP_CODE})',
            ),
            (
                AppQueryAlertsParams(environment='stag'),
                f'labels:(PAAS_BUILTIN AND {FAKE_APP_CODE} AND stag)',
            ),
            (
                AppQueryAlertsParams(environment='stag', alert_code='high_cpu_usage'),
                f'labels:(PAAS_BUILTIN AND {FAKE_APP_CODE} AND stag AND high_cpu_usage)',
            ),
            (
                AppQueryAlertsParams(alert_code='high_cpu_usage'),
                f'labels:(PAAS_BUILTIN AND {FAKE_APP_CODE} AND high_cpu_usage)',
            ),
            (
                AppQueryAlertsParams(keyword=SEARCH_KEYWORD),
                f'labels:(PAAS_BUILTIN AND {FAKE_APP_CODE}) AND alert_name:{SEARCH_KEYWORD}',
            ),
        ],
    )
    def test_to_dict(self, query_params, expected_query_string):
        assert query_params.to_dict()['query_string'] == expected_query_string


class TestQueryAlarmStrategiesParams:
    @pytest.mark.parametrize(
        'query_params, expected_query_string',
        [
            (
                AppQueryAlarmStrategiesParams(),
                [{'key': 'label_name', 'value': ['PAAS_BUILTIN', FAKE_APP_CODE]}],
            ),
            (
                AppQueryAlarmStrategiesParams(environment='stag'),
                [{'key': 'label_name', 'value': ['PAAS_BUILTIN', FAKE_APP_CODE, 'stag']}],
            ),
            (
                AppQueryAlarmStrategiesParams(environment='stag', alert_code='high_cpu_usage'),
                [{'key': 'label_name', 'value': ['PAAS_BUILTIN', FAKE_APP_CODE, 'stag', 'high_cpu_usage']}],
            ),
            (
                AppQueryAlarmStrategiesParams(alert_code='high_cpu_usage'),
                [{'key': 'label_name', 'value': ['PAAS_BUILTIN', FAKE_APP_CODE, 'high_cpu_usage']}],
            ),
            (
                AppQueryAlarmStrategiesParams(keyword=SEARCH_KEYWORD),
                [
                    {'key': 'alert_name', 'value': SEARCH_KEYWORD},
                    {'key': 'label_name', 'value': ['PAAS_BUILTIN', FAKE_APP_CODE]},
                ],
            ),
        ],
    )
    def test_to_dict(self, query_params, expected_query_string):
        assert query_params.to_dict()['conditions'] == expected_query_string
