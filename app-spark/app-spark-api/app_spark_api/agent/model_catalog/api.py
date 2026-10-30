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

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from ninja import Router

from app_spark_api.agent.model_catalog import services
from app_spark_api.agent.model_catalog.entities import ModelCatalogResponse
from app_spark_api.entities import ERROR_RESPONSES
from app_spark_api.infras.accounts.auth import login_required
from app_spark_api.infras.accounts.credentials import get_user_credential

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router(tags=["models"], auth=login_required)


@router.get(
    "",
    response={**ERROR_RESPONSES, HTTPStatus.OK: ModelCatalogResponse},
    url_name="models-list",
    summary="列出可选的模型",
)
async def list_models(request: HttpRequest):
    """列出当前部署下可选的模型、不指定模型时使用的默认模型，以及能否切换。

    不挂在项目下：决定列表的是本服务的应用身份，和 Project 没有对应关系。
    上游拿不到列表时报错，不返回空列表，免得把一次网络故障说成「没有可用模型」。
    """
    # ModelCatalog 与 ModelCatalogResponse 字段一一对应，ninja 按属性读出即可。
    return await services.list_models(get_user_credential(request))
