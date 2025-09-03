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

from typing import Optional

import requests


class RequestError(Exception):
    """Base Exception for requests"""

    def __init__(self, message: str, status_code):
        self.message = message
        super().__init__(message, status_code)


class RequestErrorWithResponse(RequestError):
    """Request error with requests.Response"""

    def __init__(self, message: str, status_code, response: Optional[requests.Response] = None):
        super().__init__(message, status_code)
        self.response = response


class AuthFailed(RequestErrorWithResponse):
    """Auth Failed for registry"""


class RetryAgain(Exception):
    """Dummy Exception to mark retry"""


class PermissionDeny(Exception):
    """Permission deny for endpoints or resources"""


class ResourceNotFound(Exception):
    """Resources not found."""


class UnSupportMediaType(Exception):
    """raise when the media type is unsupported"""
