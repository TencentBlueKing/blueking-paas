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
from app_spark_api.core.projects.constants import PROJECT_ID_PATTERN, IntRenamingStatus


class ProjectCreateRequest(Schema):
    """创建一个 Project。"""

    id: str = Field(
        pattern=PROJECT_ID_PATTERN,
        description="项目 ID，全局唯一，2-20 个字符，小写字母开头，仅含小写字母、数字与连字符，会在路径中使用",
    )
    name: str = Field(min_length=1, max_length=20, description="项目名称，不要求唯一")


class ProjectRenameRequest(Schema):
    """给一个 Project 改名。"""

    name: str = Field(min_length=1, max_length=20, description="新的项目名称，不要求唯一")


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


class ProjectIntRenamingResponse(Schema):
    """一个项目自动命名任务的当前状态。

    前端在从一句话创建项目后轮询这个接口：``pending`` 时继续等，``completed`` 时若 ``name`` 非空就
    把页面上的名字换成它，``failed`` 时保留占位名字。``name`` 为空表示模型认为描述不足以起名，同样
    是正常结束，不需要处理。

    应用 ``name`` 之前先确认页面上显示的还是占位 ID：用户可能在任务跑完前手动改过名，后端的写回会
    保留用户的名字，这时 ``name`` 只是模型给出的结果，不该盖掉用户的选择。
    """

    status: IntRenamingStatus = Field(description="任务状态：pending / completed / failed")
    name: str | None = Field(description="生成的项目名称；未完成、失败或无需起名时为 null")
    completed_at: datetime | None = Field(description="正常结束的时间；尚未结束时为 null")
    error_at: datetime | None = Field(description="失败时间；尚未失败时为 null")
    error_msg: str = Field(description="失败原因；尚未失败时为空字符串")
