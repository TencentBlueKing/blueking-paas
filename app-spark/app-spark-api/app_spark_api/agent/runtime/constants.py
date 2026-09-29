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

from enum import StrEnum

# The agent reads its whole configuration from variables under this prefix.
ENV_PREFIX = "APP_SPARK_AGENT_"

# 模型相关的 agent 变量只能由模型来源决定。extra_env 里不许出现：否则一份配置就能把固定 key
# 塞给本该拿用户态 token 的 Runtime，或者让 bkaidev 的 Runtime 回落到共享密钥。
MODEL_ENV_NAMES = frozenset(
    f"{ENV_PREFIX}{name}"
    for name in ("MODEL", "MODEL_API_KEY", "BK_AIDEV_ACCESS_TOKEN", "MODEL_BASE_URL", "MODEL_NAME")
)


class AgentRuntimeProviderType(StrEnum):
    """How an Agent Runtime is obtained for a conversation."""

    # 在本机 spawn 一个 agent 进程。开发与测试用，进程句柄只存在内存里。
    LOCAL_PROCESS = "local_process"
    # 每个会话分配一个远程沙箱；Agent Runtime 的安装与启动留待后续实现。
    E2B = "e2b"


class ModelSource(StrEnum):
    """Where an Agent Runtime's model calls go."""

    # bkaidev 的 OpenAI 兼容 LLM 网关，凭当前用户换来的 access_token 调用。
    BKAIDEV = "bkaidev"
    # 直连模型厂商，用 AGENT_DIRECT_MODEL_CONFIG 里固定的 api_key。
    DIRECT = "direct"
