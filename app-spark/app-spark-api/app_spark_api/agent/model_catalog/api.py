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
from app_spark_api.agent.model_catalog.entities import ModelCatalogResponse, ModelOptionResponse
from app_spark_api.entities import ERROR_RESPONSES
from app_spark_api.infras.accounts.auth import login_required
from app_spark_api.infras.accounts.credentials import get_user_credential

if TYPE_CHECKING:
    from django.http import HttpRequest

    from app_spark_api.agent.model_catalog.services import ModelCatalog, ModelOption

router = Router(tags=["models"], auth=login_required)


@router.get(
    "",
    response={**ERROR_RESPONSES, HTTPStatus.OK: ModelCatalogResponse},
    url_name="models-list",
    summary="列出可选的模型",
)
async def list_models(request: HttpRequest):
    """列出当前部署下可选的模型、不指定模型时使用的默认模型，以及能否切换。

    不挂在项目下：决定列表的是「本服务的应用身份 + 当前用户」，和 Project 没有对应关系。
    上游拿不到列表时报错，不返回空列表，免得把一次网络故障说成「没有可用模型」。
    """
    return _to_catalog(await services.list_models(get_user_credential(request)))


def _to_catalog(catalog: ModelCatalog) -> ModelCatalogResponse:
    """Present the models on offer as this API's own view of them."""
    return ModelCatalogResponse(
        source=catalog.source,
        switchable=catalog.switchable,
        default_code=catalog.default_code,
        models=[_to_option(model) for model in catalog.models],
    )


def _to_option(model: ModelOption) -> ModelOptionResponse:
    """Present one model on offer."""
    return ModelOptionResponse(
        code=model.code,
        name=model.name,
        context_window=model.context_window,
        supports_vision=model.supports_vision,
    )
