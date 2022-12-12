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
from datetime import datetime
from functools import partial

import pytest

from paasng.accessories.bkmonitorv3.constants import QueryAlertsParams
from tests.utils.helpers import generate_random_string

SEARCH_KEYWORD = generate_random_string(6)
FAKE_APP_CODE = generate_random_string(6)

AppQueryAlertsParams = partial(
    QueryAlertsParams, app_code=FAKE_APP_CODE, start_time=datetime.now(), end_time=datetime.now()
)


class TestQueryAlertsParams:
    @pytest.mark.parametrize(
        'query_params, expected_query_string',
        [
            (
                AppQueryAlertsParams(),
                f'labels:(BKPAAS AND {FAKE_APP_CODE} AND {FAKE_APP_CODE}_*_*)',
            ),
            (
                AppQueryAlertsParams(environment='stag'),
                f'labels:(BKPAAS AND {FAKE_APP_CODE} AND {FAKE_APP_CODE}_*stag_*)',
            ),
            (
                AppQueryAlertsParams(environment='stag', alert_code='high_cpu_usage'),
                f'labels:(BKPAAS AND {FAKE_APP_CODE} AND {FAKE_APP_CODE}_*stag_high_cpu_usage)',
            ),
            (
                AppQueryAlertsParams(alert_code='high_cpu_usage'),
                f'labels:(BKPAAS AND {FAKE_APP_CODE} AND {FAKE_APP_CODE}_*_high_cpu_usage)',
            ),
            (
                AppQueryAlertsParams(keyword=SEARCH_KEYWORD),
                f'labels:(BKPAAS AND {FAKE_APP_CODE} AND {FAKE_APP_CODE}_*_*) AND alert_name:*{SEARCH_KEYWORD}*',
            ),
        ],
    )
    def test_to_dict(self, query_params, expected_query_string):
        assert query_params.to_dict()['query_string'] == expected_query_string
