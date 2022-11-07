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


class BaseRemoteException(Exception):
    """Base exception class for remote module"""


class UnsupportedOperationError(BaseRemoteException):
    """Exception be raised when the operation is unsupported."""


class FetchRemoteSvcError(BaseRemoteException):
    pass


class RemoteClientError(Exception):
    """Base exception class for remote.client module"""


class RClientResponseError(RemoteClientError):
    """Exception when response is not valid, provides an extra "payload" field for more detailed
    error messages
    """

    def __init__(self, message, status_code: int, response_text: str):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class BaseRemoteStoreException(Exception):
    """Base exception class for remote store"""


class ServiceNotFound(BaseRemoteStoreException):
    pass


class ServiceConfigNotFound(BaseRemoteStoreException):
    pass


class GetClusterEgressInfoError(Exception):
    """Can not get app cluster egress info from engine."""
