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
from unittest import mock

import pytest

from paasng.monitoring.monitor.alert_rules.config.metric_label import get_cluster_id
from paasng.monitoring.monitor.exceptions import BKMonitorNotSupportedError
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


class FakeVersionInfo:
    def __init__(self, major: str, minor: str):
        self.major = major
        self.minor = minor

    def to_str(self):
        return f'{self.major}.{self.minor}'


@mock.patch('paasng.monitoring.monitor.alert_rules.config.metric_label._get_cluster_info_cache')
@pytest.mark.parametrize(
    'version_info',
    [
        FakeVersionInfo('1', '8'),
        FakeVersionInfo('1', '10'),
        pytest.param(FakeVersionInfo('1', '11+')),
        pytest.param(FakeVersionInfo('1', '12'), marks=pytest.mark.xfail),
        pytest.param(FakeVersionInfo('1', '12+'), marks=pytest.mark.xfail),
        pytest.param(FakeVersionInfo('1', '14+'), marks=pytest.mark.xfail),
        pytest.param(FakeVersionInfo('1', '20'), marks=pytest.mark.xfail),
    ],
)
def test_get_invalid_cluster_id(mock_get_cluster_info_cache, bk_app, version_info):
    mock_get_cluster_info_cache.return_value = {'bcs_cluster_id': generate_random_string(), 'version': version_info}
    with pytest.raises(BKMonitorNotSupportedError):
        get_cluster_id(
            app_code=generate_random_string(), run_env=generate_random_string(), module_name=generate_random_string()
        )
