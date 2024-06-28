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

from django.utils.translation import gettext_lazy as _


class IntegrityError(Exception):
    _fields_display = {
        "code": _("应用编码"),
        "name": _("应用名称"),
    }

    def __init__(self, field: str, *args, **kwargs):
        self.field = field
        super().__init__(f"field: {self.field}")

    def get_field_display(self):
        return self._fields_display.get(self.field, self.field)


class AppFieldValidationError(Exception):
    """Error when external app field validation failed"""

    REASONS = {
        "duplicated",
        "not_exist",
    }

    def __init__(self, reason: str, *args, **kwargs):
        self.reason = reason
        if reason not in self.REASONS:
            raise ValueError(f'Invalid reason: "{reason}"')
        super().__init__(f"reason: {self.reason}")


class AppResourceProtected(Exception):
    """Raised when application's resources were protected from actions"""


class LightAppAPIError(Exception):
    """轻应用错误接口"""

    def __init__(self, error_code, message: str):
        self.error_code = error_code
        self.message = message
