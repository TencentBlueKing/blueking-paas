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

"""HTTP response schemas for the model list."""

from __future__ import annotations

from ninja import Field, Schema

from app_spark_api.agent.runtime.constants import ModelSource


class ModelOptionResponse(Schema):
    """一个可选模型。"""

    id: str = Field(description="模型 ID")
    name: str = Field(description="展示名称")
    context_window: int | None = Field(description="上下文窗口")
    supports_vision: bool = Field(description="是否支持图像输入")


class ModelCatalogResponse(Schema):
    """当前部署可选的模型。"""

    source: ModelSource = Field(
        description="模型来源：bkaidev 经蓝鲸 AIDev 网关、以当前用户身份调用，可选模型来自网关；"
        "direct 直连模型厂商，只有部署时配置的那一个模型"
    )
    allow_user_switch: bool = Field(description="平台是否允许用户在会话中切换模型")
    default_model_id: str = Field(description="用户不选时使用的模型 ID，可能不在 models 中")
    models: list[ModelOptionResponse] = Field(description="可选模型，按展示顺序")
