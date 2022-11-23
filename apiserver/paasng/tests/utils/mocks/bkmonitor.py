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
import json
import random

from requests import Response

from paasng.monitoring.monitor.client import BKMonitorClient
from tests.utils.helpers import generate_random_string


def get_fake_alerts(start_time: int, end_time: int) -> dict:
    alerts = [
        {
            'id': generate_random_string(6),
            'alert_name': generate_random_string(6),
            'status': random.choice(['ABNORMAL', 'CLOSED', 'RECOVERED']),
            'description': generate_random_string(),
            'begin_time': start_time,
            'end_time': end_time,
            'stage_display': random.choice(['已通知', '未处理']),
            'assignee': [generate_random_string(6), generate_random_string(6)],
        }
        for _ in range(3)
    ]

    return {
        'code': 200,
        'result': True,
        'data': {'alerts': alerts},
    }


class StubBKMonitorClient(BKMonitorClient):
    def handle_request(self, operation, context):
        resp = Response()
        resp.status_code = 200

        data = {}
        if operation.name == 'search_alert':
            data = get_fake_alerts(context['json']['start_time'], context['json']['end_time'])

        resp._content = json.dumps(data).encode('utf-8')
        return resp
