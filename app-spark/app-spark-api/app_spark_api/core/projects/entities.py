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

from datetime import datetime

from ninja import Field, Schema

from app_spark_api.agent.conversations.entities import MAX_RUN_CONTENT_LENGTH, ConversationResponse
from app_spark_api.core.projects.constants import PROJECT_ID_PATTERN


class ProjectCreateRequest(Schema):
    """创建一个 Project。"""

    id: str = Field(
        pattern=PROJECT_ID_PATTERN,
        description="项目 ID，全局唯一，2-20 个字符，小写字母开头，仅含小写字母、数字与连字符，会在路径中使用",
    )
    name: str = Field(min_length=1, max_length=20, description="项目名称，同租户内唯一")


class ProjectRenameRequest(Schema):
    """给一个 Project 改名。"""

    name: str = Field(min_length=1, max_length=20, description="新的项目名称，同租户内唯一")


class ProjectResponse(Schema):
    """一个 Project 对象。"""

    id: str = Field(description="项目 ID")
    name: str = Field(description="项目名称")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")


class ProjectFromPromptRequest(Schema):
    """用第一句话创建一个 Project。"""

    # 和 runs 接口用同一个上限：这句话随后要原样作为第一轮对话发出去。
    content: str = Field(
        min_length=1,
        max_length=MAX_RUN_CONTENT_LENGTH,
        description="用户的第一句话，客户端随后要把它作为第一轮对话发出",
    )


class ProjectFromPromptResponse(Schema):
    """从一句话建出来的 Project，以及承接第一轮对话的会话。"""

    project: ProjectResponse = Field(description="新建的 Project，名称暂时与 ID 相同")
    conversation: ConversationResponse = Field(description="新建的会话，用它的 number 发起第一轮对话")
