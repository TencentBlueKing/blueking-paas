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

"""Deciding how a new Agent Runtime calls its model, and getting it a token when that is bkaidev."""

from typing import TYPE_CHECKING

from django.conf import settings

from app_spark_api.agent.runtime.constants import ModelSource
from app_spark_api.agent.runtime.entities import (
    BkAidevModelAccess,
    structure_bkaidev_model_config,
    structure_direct_model_config,
)
from app_spark_api.agent.runtime.exceptions import ModelAccessConfigurationError, ModelCredentialMissingError
from app_spark_api.infras.bk_access_token import AccessTokenClient

if TYPE_CHECKING:
    import httpx2

    from app_spark_api.agent.runtime.entities import ModelAccess
    from app_spark_api.infras.bk_access_token import UserCredential


def get_model_source() -> ModelSource:
    """Return where this service's Agent Runtimes send their model calls.

    :raises ModelAccessConfigurationError: If AGENT_MODEL_SOURCE is not a known source.
    """
    try:
        return ModelSource(settings.AGENT_MODEL_SOURCE)
    except ValueError as exc:
        raise ModelAccessConfigurationError(f"Unknown AGENT_MODEL_SOURCE: {settings.AGENT_MODEL_SOURCE!r}") from exc


async def resolve_model_access(
    credential: UserCredential | None,
    *,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> ModelAccess:
    """Return what a Runtime about to be started needs to call its model as this user.

    Meant to be handed to a provider as a ModelAccessResolver, so it runs only when a Runtime is
    really being started. Asks the token service every time and keeps nothing: the token service
    hands back the user's current token instead of issuing a new one, so there is no local copy
    to store, expire, or leak.

    Example::

        credential = get_user_credential(request)
        await provider.ensure(..., model_access=lambda: resolve_model_access(credential))

    :param credential: The user's BlueKing login, None when the request carried none.
    :param transport: httpx transport for the token service; tests inject MockTransport.
    :return: The fixed vendor model and key for direct calls, or the bkaidev address, model and
        the user's token.
    :raises ModelAccessConfigurationError: If the model source or its settings are invalid.
    :raises ModelCredentialMissingError: If bkaidev is used and the request has no login.
    :raises AccessTokenUnavailableError: If the token service could not give a token.
    """
    if get_model_source() == ModelSource.DIRECT:
        return structure_direct_model_config(settings.AGENT_DIRECT_MODEL_CONFIG)

    # 先校验配置再看登录态：配置缺失是运维问题，不该让用户误以为重新登录就能解决。
    config = structure_bkaidev_model_config(settings.BKAIDEV_MODEL_CONFIG)
    if credential is None:
        raise ModelCredentialMissingError("Calling bkaidev needs the user's BlueKing login, and the request has none")

    access_token = await AccessTokenClient(config.token, transport=transport).fetch_user_token(credential)
    return BkAidevModelAccess(base_url=config.base_url, model_name=config.model_name, access_token=access_token)
