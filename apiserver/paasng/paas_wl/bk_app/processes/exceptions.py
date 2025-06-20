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

"""Custom exceptions for processes module"""

import re
from typing import Optional

from django.utils.encoding import force_str
from kubernetes.dynamic.exceptions import NotFoundError

from paas_wl.infras.resources.kube_res.exceptions import AppEntityDeserializeError


class ProcessOperationTooOften(Exception):
    """进程操作过于频繁"""


class ProcessNotFound(Exception):
    """Unable to find the process"""


class ScaleProcessError(Exception):
    """Unable to scale process due to internal errors.

    :param proc_type: The process type, optional.
    :param exception: The original exception, optional.
    :param message: An extra error message, optional.
    """

    def __init__(
        self, proc_type: Optional[str] = None, exception: Optional[Exception] = None, message: Optional[str] = None
    ):
        self.proc_type = proc_type
        self.exception = exception
        self.message = message

        # Build and initialize error message
        messages = []
        if proc_type:
            messages.append(f"scale {proc_type} failed")
        if exception:
            messages.append(f"reason: {exception}")
        if message:
            messages.append(message)
        super().__init__(", ".join(messages))

    def caused_by_not_found(self) -> bool:
        """Check if the error was caused by missing namespace."""
        if isinstance(self.exception, NotFoundError) and re.search(  # noqa: SIM103
            r"namespaces .* not found", force_str(self.exception.summary())
        ):
            return True

        return False


class UnknownProcessTypeError(AppEntityDeserializeError):
    """Unable to detect process type from Deployment/Pod"""


class InstanceNotFound(Exception):
    """Unable to find the instance"""
