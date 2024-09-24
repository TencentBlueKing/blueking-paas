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

import atexit
import random
from datetime import datetime
from functools import partial
from pathlib import Path

import pytest
from filelock import FileLock

from paasng.infras.bkmonitorv3.constants import SpaceType
from paasng.infras.bkmonitorv3.exceptions import BkMonitorApiError
from paasng.infras.bkmonitorv3.models import BKMonitorSpace
from paasng.infras.bkmonitorv3.params import QueryAlarmStrategiesParams, QueryAlertsParams
from tests.utils.helpers import create_app, generate_random_string

pytestmark = pytest.mark.django_db

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

AppQueryAlertsParamsWithBizIds = partial(
    QueryAlertsParams,
    bk_biz_ids=[random.randint(-5000000, -4000000)],
    start_time=datetime.now(),
    end_time=datetime.now(),
)

AppQueryAlarmStrategiesParams = partial(QueryAlarmStrategiesParams, app_code=FAKE_APP_CODE)


@pytest.fixture()
def bk_monitor_space():
    app = create_app()
    app.code = FAKE_APP_CODE
    app.save()

    return BKMonitorSpace.objects.create(
        application=app,
        id=40000,
        space_type_id=SpaceType.SAAS,
        space_id="100",
        space_name="蓝鲸应用-test",
        extra_info={"test": "test"},
    )


class TestQueryAlertsParams:
    @pytest.mark.parametrize(
        ("query_params", "expected_query_string"),
        [
            (
                AppQueryAlertsParams(),
                None,
            ),
            (
                AppQueryAlertsParams(environment="stag"),
                "labels:(stag)",
            ),
            (
                AppQueryAlertsParams(environment="stag", alert_code="high_cpu_usage"),
                "labels:(stag AND high_cpu_usage)",
            ),
            (
                AppQueryAlertsParams(alert_code="high_cpu_usage"),
                "labels:(high_cpu_usage)",
            ),
            (
                AppQueryAlertsParams(keyword=SEARCH_KEYWORD),
                f"alert_name:({SEARCH_KEYWORD} OR *{SEARCH_KEYWORD}*)",
            ),
        ],
    )
    def test_to_dict(self, query_params, expected_query_string, bk_monitor_space):
        result = query_params.to_dict()
        assert result["bk_biz_ids"] == [int(bk_monitor_space.iam_resource_id)]
        if query_string := result.get("query_string"):
            assert query_string == expected_query_string

    @pytest.mark.parametrize(
        ("query_params", "expected_query_string"),
        [
            (
                AppQueryAlertsParamsWithBizIds(),
                None,
            ),
            (
                AppQueryAlertsParamsWithBizIds(environment="stag"),
                "labels:(stag)",
            ),
            (
                AppQueryAlertsParamsWithBizIds(environment="stag", alert_code="high_cpu_usage"),
                "labels:(stag AND high_cpu_usage)",
            ),
            (
                AppQueryAlertsParamsWithBizIds(alert_code="high_cpu_usage"),
                "labels:(high_cpu_usage)",
            ),
            (
                AppQueryAlertsParamsWithBizIds(keyword=SEARCH_KEYWORD),
                f"alert_name:({SEARCH_KEYWORD} OR *{SEARCH_KEYWORD}*)",
            ),
        ],
    )
    def test_to_dict_with_bk_biz_id(self, query_params, expected_query_string, bk_monitor_space):
        result = query_params.to_dict()
        assert result["bk_biz_ids"] == query_params.bk_biz_ids
        if query_string := result.get("query_string"):
            assert query_string == expected_query_string

    @pytest.mark.parametrize(
        ("query_params"),
        [
            partial(QueryAlertsParams, start_time=datetime.now(), end_time=datetime.now())(),
            partial(
                QueryAlertsParams,
                app_code=FAKE_APP_CODE,
                bk_biz_ids=[random.randint(-5000000, -4000000)],
                start_time=datetime.now(),
                end_time=datetime.now(),
            )(),
        ],
    )
    def test_to_dict_exception(self, query_params):
        with pytest.raises(BkMonitorApiError, match="params must have one of app_code or bk_biz_ids, not both"):
            query_params.to_dict()


class TestQueryAlarmStrategiesParams:
    @pytest.mark.parametrize(
        ("query_params", "expected_query_string"),
        [
            (
                AppQueryAlarmStrategiesParams(),
                [{"key": "label_name", "value": []}],
            ),
            (
                AppQueryAlarmStrategiesParams(environment="stag"),
                [{"key": "label_name", "value": ["stag"]}],
            ),
            (
                AppQueryAlarmStrategiesParams(environment="stag", alert_code="high_cpu_usage"),
                [{"key": "label_name", "value": ["stag", "high_cpu_usage"]}],
            ),
            (
                AppQueryAlarmStrategiesParams(alert_code="high_cpu_usage"),
                [{"key": "label_name", "value": ["high_cpu_usage"]}],
            ),
            (
                AppQueryAlarmStrategiesParams(keyword=SEARCH_KEYWORD),
                [
                    {"key": "strategy_name", "value": SEARCH_KEYWORD},
                    {"key": "label_name", "value": []},
                ],
            ),
        ],
    )
    def test_to_dict(self, query_params, expected_query_string, bk_monitor_space):
        result = query_params.to_dict()
        assert result["bk_biz_id"] == bk_monitor_space.iam_resource_id
        assert result["conditions"] == expected_query_string
