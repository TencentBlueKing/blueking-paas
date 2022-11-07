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
import uuid
from unittest import mock

import arrow
import pytest

from paasng.engine.monitoring import count_frozen_deployments

from .setup_utils import create_fake_deployment

pytestmark = pytest.mark.django_db


# Get current datetime when compiling
_NOW = arrow.now()


@pytest.fixture
def bk_deployment(bk_module):
    deployment = create_fake_deployment(bk_module)
    deployment.build_process_id = uuid.uuid4()
    # Deployment was created 15 seconds ago
    deployment.created = _NOW.shift(seconds=-15).datetime
    deployment.save()
    return deployment


class TestCountFrozenDeployments:
    def test_no_build_process_id(self, bk_deployment):
        bk_deployment.build_process_id = None
        bk_deployment.save()
        assert count_frozen_deployments(edge_seconds=10, now=_NOW) == 1

    @pytest.mark.parametrize(
        'log_lines,cnt',
        [
            # No log lines
            ([], 1),
            # Log lines has no created field
            (
                [
                    {
                        "stream": "STDOUT",
                        "line": "foo",
                    },
                ],
                0,
            ),
            # Log lines were fresh
            (
                [
                    {"stream": "STDOUT", "line": "foo", "created": _NOW.format()},
                ],
                0,
            ),
            # Log lines were staled
            (
                [
                    {"stream": "STDOUT", "line": "foo", "created": _NOW.shift(seconds=-30).format()},
                ],
                1,
            ),
        ],
    )
    def test_different_log_lines(self, bk_deployment, log_lines, cnt):
        with mock.patch('paasng.engine.monitoring.EngineDeployClient') as mocked_client:
            mocked_client().get_build_process_status.return_value = {'lines': log_lines}
            assert count_frozen_deployments(edge_seconds=10, now=_NOW.datetime) == cnt

    def test_now_not_provided(self, bk_deployment):
        bk_deployment.created = arrow.now().datetime
        bk_deployment.save()
        assert count_frozen_deployments(edge_seconds=10) == 0
