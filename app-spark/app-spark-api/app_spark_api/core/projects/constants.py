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

from datetime import timedelta
from enum import StrEnum


class IntRenamingStatus(StrEnum):
    """一个项目自动命名任务的结局，由 ``ProjIntRenaming`` 的时间字段推导。

    * PENDING：还在排队或执行；
    * COMPLETED：正常结束，生成的名字可以为空；
    * FAILED：执行失败，``error_msg`` 说明原因。
    """

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# 自动命名过了这么久还没有结论就记为失败：worker 被杀、任务丢失或写回失败时，记录不会自己结束。
# 要盖住排队、单次请求超时、SDK 重试和校验不过时的重答。
INT_RENAMING_TIMEOUT = timedelta(minutes=10)


# Project ID 由调用方指定，所以它的形状必须在入口处卡死，而不只是「建议这么写」。
#
# 首字符限定为字母，是为了避免出现纯数字 ID——那种 ID 在 URL 和日志里很容易被当成别的东西。
# 长度 2-20，上限对齐 `Project.id` 的 max_length。
PROJECT_ID_PATTERN = r"^[a-z][a-z0-9-]{1,19}$"

# `/projects/` 下不属于任何一个 Project 的操作，统一挂在这个路径段下面，例如
# `/projects/-/create-from-prompt/`。它以连字符开头，按 PROJECT_ID_PATTERN 永远不可能是项目 ID，
# 所以不需要维护保留词表，也不会和 `/projects/{project_id}/...` 抢路由；以后再加同类操作，
# 继续往这个前缀下面挂即可。
COLLECTION_ACTIONS_SEGMENT = "-"

# 从一句话创建的项目由服务端生成 ID：`p-` 加 10 位小写字母和数字，总长 12，落在 PROJECT_ID_PATTERN 内。
# 36^10 的空间撞上的概率可以忽略，重试只是兜底。
GENERATED_PROJECT_ID_PREFIX = "p-"
GENERATED_PROJECT_ID_SUFFIX_LENGTH = 10
GENERATED_PROJECT_ID_MAX_ATTEMPTS = 5

# 项目名称的长度上限，与 `Project.name` 的 max_length 一致。
PROJECT_NAME_MAX_LENGTH = 20

# 删除在请求内同步完成；外部存储不响应时也不能无限占住 Web worker。
DELETE_PROJECT_TIMEOUT_SECONDS = 120
