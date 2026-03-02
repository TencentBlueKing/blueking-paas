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

from dataclasses import dataclass
from unittest import mock

from rest_framework.test import APIRequestFactory

request_factory = APIRequestFactory(enforce_csrf_checks=False)


def get_response(request):
    """Dummy response callback for middleware"""
    return mock.MagicMock()


@dataclass
class MockUser:
    """Mock user object for testing"""

    username: str
    time_zone: str | None = None
    is_authenticated: bool = True


@dataclass
class MockUserWithoutTimezone:
    """Mock user without timezone object for testing"""

    username: str
    is_authenticated: bool = True
