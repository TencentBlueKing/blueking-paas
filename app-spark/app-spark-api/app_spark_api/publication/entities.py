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

"""发布接口的请求与响应结构。"""

from datetime import datetime
from typing import TYPE_CHECKING

import attrs
from ninja import Field, Schema

if TYPE_CHECKING:
    from app_spark_api.publication.services import AppNameValidation, PublicationState


class DeploymentCreateRequest(Schema):
    """把一个版本部署到开发者中心；已发布时即为更新版本。"""

    version_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description=(
            "要发布的版本，须属于该项目。暂不支持选版本，前端不传，发最新版本（见 latest_version_id）。"
            "暂时为会话检查点的 tag，如 app-spark/checkpoint/<run_id>"
        ),
    )
    app_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        description=(
            "首次发布时创建的开发者中心应用名称，AppSpark 不保存。不传时用项目名称（过滤后为空则用项目 ID）。"
            "应用 ID 固定为项目 ID。已创建应用后忽略"
        ),
    )


class OnlineVersionResponse(Schema):
    """线上正在服务的版本。"""

    version_id: str = Field(description="线上版本号")
    url: str = Field(description="可分享的应用访问地址")
    published_at: datetime | None = Field(description="该版本的发布时间")


class PublicationTaskResponse(Schema):
    """进行中的任务。"""

    kind: str = Field(description="任务类型，目前只有 deployment（发布、更新版本）")
    version_id: str = Field(description="发布的版本号")
    is_update: bool = Field(description="发起时是否已有线上版本，即是否为更新版本")
    stage: str = Field(description="当前步骤：binding、packaging、uploading、deploying")
    started_at: datetime = Field(description="发起时间")


class PublicationFailureResponse(Schema):
    """最近结束的任务失败了时的信息。"""

    kind: str = Field(description="失败的任务类型")
    version_id: str = Field(description="失败时发布的版本号")
    is_update: bool = Field(description="失败的是否为更新版本")
    error: str = Field(description="失败原因，可直接展示；更多信息到 detail_url 指向的开发者中心页面查看")
    failed_at: datetime | None = Field(description="失败时间")
    detail_url: str | None = Field(description="开发者中心里的详情页，未创建应用或未配置站点地址时为空")


class UnseenResultResponse(Schema):
    """发布面板打开时要主动展开的最近一次任务结果，用户点开看过后不再出现。"""

    kind: str = Field(description="任务类型")
    status: str = Field(description="任务结果：successful 或 failed")


class BkPaaSLinksResponse(Schema):
    """开发者中心里管理该应用的页面。"""

    logs: str = Field(description="日志查询")
    deployments: str = Field(description="部署管理")
    env_vars: str = Field(description="环境变量")
    members: str = Field(description="成员管理")


class PublicationResponse(Schema):
    """项目在开发者中心的发布状态。"""

    online: OnlineVersionResponse | None = Field(description="线上版本，未发布时为空")
    task: PublicationTaskResponse | None = Field(description="进行中的任务，没有时为空")
    last_failure: PublicationFailureResponse | None = Field(description="最近一次失败")
    unseen_result: UnseenResultResponse | None = Field(
        description="不为空时前端主动展开最近一次任务结果；用户点开看过（DELETE unseen-result/）或有任务进行中时为空"
    )
    app_code: str | None = Field(description="已创建的开发者中心应用 ID（即项目 ID）；为空表示下次发布会新建应用")
    default_app_name: str | None = Field(description="首次发布时预填的应用名称，可在发布时修改；已创建应用后为空")
    bkpaas_links: BkPaaSLinksResponse | None = Field(description="开发者中心页面链接，首次发布创建应用后才有")
    latest_version_id: str | None = Field(
        description="不指定版本时会发布的最新版本；为空表示还没有可发布的版本，发布按钮应禁用"
    )

    @classmethod
    def from_state(cls, state: PublicationState) -> PublicationResponse:
        """Build the response from the publication state."""
        online = None
        if state.online is not None:
            online = OnlineVersionResponse(**attrs.asdict(state.online))

        # 任务是模型，字段比响应多，只挑要展示的。
        task = None
        if state.task is not None:
            task = PublicationTaskResponse(
                kind=state.task.kind,
                version_id=state.task.version_id,
                is_update=state.task.is_update,
                stage=state.task.stage,
                started_at=state.task.started_at,
            )

        last_failure = None
        if state.last_failure is not None:
            last_failure = PublicationFailureResponse(**attrs.asdict(state.last_failure))

        unseen_result = None
        if state.unseen_result is not None:
            unseen_result = UnseenResultResponse(**attrs.asdict(state.unseen_result))

        bkpaas_links = None
        if state.console_links is not None:
            bkpaas_links = BkPaaSLinksResponse(**attrs.asdict(state.console_links))

        return cls(
            online=online,
            task=task,
            last_failure=last_failure,
            unseen_result=unseen_result,
            app_code=state.app_code,
            default_app_name=state.default_app_name,
            bkpaas_links=bkpaas_links,
            latest_version_id=state.latest_version_id,
        )


class AppNameValidateResponse(Schema):
    """首次发布时某个应用名称能否用来创建开发者中心应用。"""

    name: str = Field(description="按开发者中心的规则过滤、截断后实际会用的名称；什么也不剩时为空字符串")
    is_available: bool = Field(description="能否用这个名称创建应用")
    problem: str | None = Field(
        description="不能用时为开发者中心的错误码，unique 表示已被其他应用使用；过滤后为空时为 invalid。能用时为空"
    )
    message: str | None = Field(description="给用户看的说明，能用时为空")

    @classmethod
    def from_validation(cls, validation: AppNameValidation) -> AppNameValidateResponse:
        """Build the response from a name validation."""
        return cls(
            name=validation.name,
            is_available=validation.is_available,
            problem=validation.problem,
            message=validation.message,
        )
