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
from typing import Any

from blue_krill.web.drf_utils import stringify_validation_error
from rest_framework.exceptions import ValidationError


class AppDescriptionNotFoundError(Exception):
    """Raised when app description is not found"""


class DescriptionValidationError(Exception):
    """Raised when any given description was invalid

    :param detail: detailed error, should be compatible with DRF's error detail
    :param message: the simplified error string, which might not include all error fields
    """

    def __init__(self, detail: Any, message: str = ''):
        self.detail = detail
        if not message:
            message = self.build_message_by_detail(detail)
        self.message = message
        super().__init__(message)

    @staticmethod
    def build_message_by_detail(detail: Any) -> str:
        """Try build a user-friendly error message from detail"""
        if isinstance(detail, dict):
            # Get a random item from dict
            item = list(detail.items())[0]
            return f'{item[0]}: {item[1]}'
        elif isinstance(detail, (list, tuple)):
            return detail[0]
        return str(detail)

    @classmethod
    def from_validation_error(cls, error: ValidationError) -> 'DescriptionValidationError':
        """Transform DRF's ValidationError into DescriptionValidationError"""
        err_messages = stringify_validation_error(error)
        return cls(error.detail, err_messages[0])


class ControllerError(Exception):
    """An error occurred when controller is processing the input data"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
