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

import requests

from .exceptions import SandboxError


def extract_error_detail(resp: requests.Response) -> str | None:
    """Best-effort extract the daemon's human-readable error message.

    Both the sandbox daemon and the resident daemon returns JSON error bodies shaped as
    ``{"message": ..., "timestamp": ..., "path": ..., "method": ...}`` (see ``httputil.ErrorResponse``).
    Non-JSON or missing ``message`` bodies yield ``None`` so callers can fall back to a generic message.
    """
    try:
        body = resp.json()
    except ValueError:
        return None
    if isinstance(body, dict):
        msg = body.get("message")
        if isinstance(msg, str) and msg:
            return msg
    return None


def public_detail(exc: SandboxError) -> str | None:
    """Return the client-safe error text for API responses, or None if unavailable.

    Only exc.detail is safe to expose; str(exc) is log-only.
    """
    if not isinstance(exc, SandboxError):
        return None
    detail = exc.detail
    if not isinstance(detail, str):
        return None
    return detail.strip() or None
