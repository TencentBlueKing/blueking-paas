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

"""E2B sandboxes: provision one per conversation, renew it, and stop its Agent."""

from __future__ import annotations

from . import constants, health
from .claim import _SandboxClaim
from .constants import (
    ABANDONED_CLAIM_SECONDS,
    HEALTH_POLL_INTERVAL_SECONDS,
    PROVISION_TIMEOUT_SECONDS,
    RENEW_TIMEOUT_SECONDS,
    REUSE_HEALTH_ATTEMPTS,
    REUSE_HEALTH_RETRY_INTERVAL_SECONDS,
    STARTUP_GRACE_MARGIN_SECONDS,
    STOP_GRACE_SECONDS,
)
from .health import probe_agent_health, read_agent_health
from .provider import E2BProvider

__all__ = [
    "ABANDONED_CLAIM_SECONDS",
    "HEALTH_POLL_INTERVAL_SECONDS",
    "PROVISION_TIMEOUT_SECONDS",
    "RENEW_TIMEOUT_SECONDS",
    "REUSE_HEALTH_ATTEMPTS",
    "REUSE_HEALTH_RETRY_INTERVAL_SECONDS",
    "STARTUP_GRACE_MARGIN_SECONDS",
    "STOP_GRACE_SECONDS",
    "E2BProvider",
    "_SandboxClaim",
    "constants",
    "health",
    "probe_agent_health",
    "read_agent_health",
]
