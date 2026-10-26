# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import functools
import logging
import time
from typing import Callable

from rest_framework.generics import get_object_or_404

from paasng.misc.metrics import AGENT_SANDBOX_REQUEST_DURATION_HISTOGRAM, AGENT_SANDBOX_REQUESTS_COUNTER
from paasng.platform.agent_sandbox.constants import SandboxOperation, SandboxRequestResult
from paasng.platform.agent_sandbox.models import Sandbox

logger = logging.getLogger(__name__)


def record_sandbox_request(operation: SandboxOperation):
    """统计一次沙箱接口调用的次数与耗时.

    刻意做成 "逐个 action 显式装饰", 让 operation 与具体方法一一对应.

    - 经由 DRF 异常处理链转成响应的失败 (如 4xx/5xx 错误码) 按状态码判定为 failure
    - 未被捕获而冒泡的异常也记为 failure, 然后原样抛出

    :param operation: 本 action 对应的 operation 标签值
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            started = time.monotonic()
            try:
                response = func(self, request, *args, **kwargs)
            except Exception:
                _record(operation, started, SandboxRequestResult.FAILURE, request)
                raise

            result = SandboxRequestResult.SUCCESS if response.status_code < 400 else SandboxRequestResult.FAILURE
            _record(operation, started, result, request)
            return response

        return wrapper

    return decorator


def _record(operation: SandboxOperation, started: float, result: SandboxRequestResult, request) -> None:
    """写入指标, 埋点失败只记日志."""
    try:
        labels = {"operation": operation.value, "result": result.value}
        AGENT_SANDBOX_REQUESTS_COUNTER.labels(app_code=_request_app_code(request), **labels).inc()
        AGENT_SANDBOX_REQUEST_DURATION_HISTOGRAM.labels(**labels).observe(time.monotonic() - started)
    except Exception:
        logger.warning("failed to record sandbox request metric", exc_info=True)


def _request_app_code(request) -> str:
    """请求来源应用 code, 取自网关透传的应用信息."""
    app = getattr(request, "app", None)
    return getattr(app, "bk_app_code", None) or ""


class SandboxViewMixin:
    """A mixin for sandbox-related views, provides shortcut to retrieve
    a sandbox instance and perform object-level permission checks."""

    check_object_permissions: Callable

    def get_sandbox_with_perm(self, request, sandbox_id: str) -> Sandbox:
        sandbox = get_object_or_404(Sandbox, uuid=sandbox_id, deleted_at__isnull=True)
        self.check_object_permissions(request, sandbox.application)
        return sandbox
