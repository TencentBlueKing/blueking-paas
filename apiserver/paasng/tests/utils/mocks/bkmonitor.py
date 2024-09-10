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

import random
from typing import Dict, List

from paasng.infras.bkmonitorv3.client import BkMonitorClient
from paasng.infras.bkmonitorv3.params import QueryAlarmStrategiesParams, QueryAlertsParams
from tests.utils.helpers import generate_random_string


def get_fake_alerts(start_time: int, end_time: int) -> List:
    alerts = [
        {
            "id": generate_random_string(6),
            "bk_biz_id": -5000000,
            "alert_name": generate_random_string(6),
            "status": random.choice(["ABNORMAL", "CLOSED", "RECOVERED"]),
            "description": generate_random_string(),
            "begin_time": start_time,
            "end_time": end_time,
            "stage_display": random.choice(["已通知", "未处理"]),
            "assignee": [generate_random_string(6), generate_random_string(6)],
            "labels": [random.choice(["stag", "prod"])],
        }
        for _ in range(3)
    ]
    return alerts


def get_fake_alarm_strategies() -> Dict:
    alarm_strategies = [
        {
            "id": generate_random_string(6),
            "bk_biz_id": random.randint(-5000000, -4000000),
            "name": generate_random_string(6),
            "is_enabled": random.choice(["true", "false"]),
            "labels": [generate_random_string(6) for _ in range(random.randint(1, 4))],
            "notice": {"user_groups": [random.randint(1, 4) for _ in range(random.randint(1, 4))]},
            "detects": [
                {
                    "trigger_config": {"count": random.randint(1, 4), "check_window": random.randint(1, 10)},
                    "connector": random.choice(["and", "or"]),
                }
            ],
            "items": [
                {
                    "algorithms": [
                        {
                            "type": generate_random_string(6),
                            "config": generate_random_string(6),
                            "level": random.randint(1, 3),
                        }
                    ]
                }
            ],
        }
        for _ in range(3)
    ]
    user_group_list = [
        {"user_group_id": generate_random_string(4), "user_group_name": generate_random_string(4)} for _ in range(3)
    ]
    return {
        "strategy_config_list": alarm_strategies,
        "user_group_list": user_group_list,
        "strategy_config_link": generate_random_string(10),
    }


def get_fake_space_biz_id(app_codes: List) -> List:
    return [
        {
            "biz_id": -5000000,
            "app_code": code,
            "name": generate_random_string(6),
            "type": random.choice(["true", "false"]),
            "is_plugin_app": random.choice(["default", "engineless_app", "cloud_native"]),
            "logo_url": "http://get_logo_url",
        }
        for code in app_codes
    ]


class StubBKMonitorClient(BkMonitorClient):
    """蓝鲸监控提供的API，仅供单元测试使用"""

    def query_alerts(self, query_params: QueryAlertsParams) -> List:
        query_data = query_params.to_dict()
        return get_fake_alerts(query_data["start_time"], query_data["end_time"])

    def query_space_biz_id(self, app_codes: List) -> List:
        return get_fake_space_biz_id(app_codes)

    def query_alarm_strategies(self, query_params: QueryAlarmStrategiesParams) -> Dict:
        query_params.to_dict()
        return get_fake_alarm_strategies()
