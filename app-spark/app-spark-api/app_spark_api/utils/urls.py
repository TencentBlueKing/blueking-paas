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

from typing import Any

from django.conf import settings
from django.urls import reverse
from django.urls.base import get_script_prefix


def _force_script_prefix() -> str:
    """Return FORCE_SCRIPT_NAME as a prefix ending with ``/``, or ``/`` if unset."""
    name = (getattr(settings, "FORCE_SCRIPT_NAME", None) or "").rstrip("/")
    return f"{name}/" if name else "/"


def _strip_prefix(url: str, prefix: str) -> str:
    if prefix != "/" and url.startswith(prefix):
        return "/" + url[len(prefix) :]
    return url


def reverse_public(viewname: str, kwargs: dict[str, Any] | None = None) -> str:
    """Reverse ``viewname`` to the browser-facing path, including FORCE_SCRIPT_NAME.

    ``django.urls.reverse`` reads a thread-local script prefix. Under ASGI that
    prefix is set on the handler's context and is not visible to sync views, so
    ``reverse()`` alone would omit the public ingress prefix. Settings are the
    source of truth here.

    Example::

        reverse_public("api:accounts-userinfo")
        # '/api-svc/api/accounts/userinfo/' when FORCE_SCRIPT_NAME is ``/api-svc``
    """
    url = reverse(viewname, kwargs=kwargs)
    prefix = _force_script_prefix()
    if prefix != "/" and not url.startswith(prefix):
        return prefix.rstrip("/") + url
    return url


def to_path_info(path: str) -> str:
    """Strip FORCE_SCRIPT_NAME (and the thread-local script prefix) from ``path``.

    Providers that reach this process without going through Ingress should join
    the result onto ``callback_base_url``. Providers that call in through the
    public prefix should keep the original path.

    Example::

        to_path_info("/api-svc/api/internal/conversations/<uuid>/state/")
        # '/api/internal/conversations/<uuid>/state/'
        # when FORCE_SCRIPT_NAME is ``/api-svc``.
    """
    path = _strip_prefix(path, _force_script_prefix())
    return _strip_prefix(path, get_script_prefix())


def reverse_path_info(viewname: str, kwargs: dict[str, Any] | None = None) -> str:
    """Reverse ``viewname`` to the PATH_INFO Django will see.

    Example::

        reverse_path_info("api:internal-append-messages", kwargs={"conversation_id": cid})
        # '/api/internal/conversations/<uuid>/messages'
        # even when FORCE_SCRIPT_NAME is ``/api-svc``.
    """
    return to_path_info(reverse_public(viewname, kwargs=kwargs))
