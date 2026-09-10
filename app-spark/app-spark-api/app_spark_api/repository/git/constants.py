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

"""Git 仓库生命周期的取值。不用 Django choices：状态集会随后续阶段变。"""

from __future__ import annotations

# ProjectGitRepository.status 的取值。
# STATUS_PENDING git 项目等待初始化。
STATUS_PENDING = "pending"
# STATUS_READY git 项目初始化完成。
STATUS_READY = "ready"
# STATUS_FAILED git 项目初始化失败。
STATUS_FAILED = "failed"

WRITE_TOKEN_SCOPE = "write:repository"
READ_TOKEN_SCOPE = "read:repository"

DEFAULT_BRANCH = "main"
DEFAULT_BACKEND_TYPE = "forgejo"


def write_token_name(project_id: str) -> str:
    """Deterministic token name so a lost create-response can be found and revoked."""
    return f"app-spark-{project_id}-write"


def read_token_name(project_id: str) -> str:
    """Name used for the short-lived read token that provision issues only to verify isolation."""
    return f"app-spark-{project_id}-read"
