"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
from contextlib import suppress
from functools import lru_cache, wraps
from typing import Optional, Type

from bkapi_client_core.apigateway import APIGatewayClient, Operation
from bkapi_client_core.apigateway import OperationGroup as _OperationGroup
from bkapi_client_core.apigateway import bind_property
from bkapi_client_core.config import HookEvent
from bkapi_client_core.exceptions import ResponseError
from bkapi_client_core.session import Session
from blue_krill.web.std_error import APIError
from django.conf import settings
from django.utils.translation import get_language
from requests.models import Request

from paasng.pluginscenter.definitions import PluginBackendAPIResource

logger = logging.getLogger(__name__)


class OperationGroup(_OperationGroup):
    call: Operation


class DynamicClient(APIGatewayClient):
    group: OperationGroup

    def __init__(self, api_name: str, stage: Optional[str] = None, endpoint: str = "", session=None):
        self._api_name = api_name
        super().__init__(stage, endpoint, session)

    def with_group(self, group_cls: Type[OperationGroup]):
        self.group = group_cls("group", self)
        self.group.call = exception_transformer_decorator(self.group.call)
        return self

    def with_bkapi_authorization(self, **auth):
        self.update_bkapi_authorization(**auth)
        return self

    def with_i18n_hook(self):
        registry_i18n_hook(self.session)
        return self


@lru_cache
def _make_operation_group(resource: PluginBackendAPIResource) -> Type[OperationGroup]:
    group_cls = type(
        "group",
        (OperationGroup,),
        {"call": bind_property(Operation, name="call", method=resource.method, path=resource.path)},
    )
    assert issubclass(group_cls, OperationGroup)
    return group_cls


def make_client(resource: PluginBackendAPIResource, bk_username: Optional[str] = None) -> OperationGroup:
    auth = {"bk_app_code": settings.BK_APP_CODE, "bk_app_secret": settings.BK_APP_SECRET}
    if bk_username:
        auth["bk_username"] = bk_username
    return (
        DynamicClient(
            api_name=resource.apiName,
            stage=settings.BK_PLUGIN_APIGW_SERVICE_STAGE,
            endpoint=settings.BK_API_URL_TMPL,
        )
        .with_group(_make_operation_group(resource))
        .with_bkapi_authorization(**auth)
        .with_i18n_hook()
        .group
    )


def transform_exception(exc: Exception):
    """transfrom given exception to APIError exception

    :raise: APIError
    """
    if not isinstance(exc, ResponseError):
        logger.exception("请求第三方系统接口时触发未知异常")
        raise APIError(code="UnknownError", message="system error") from exc

    error_message = ""
    error_code_string = "APIError"
    error_code_num = -1
    if request_id := exc.request_id:
        error_message += f"<request_id: {request_id}> "

    response_data = None
    response_message = "[invalid response body]"
    response = exc.response
    if response is not None:
        with suppress(Exception):
            response_data = response.json()

    if isinstance(response_data, dict):
        response_message = response_data.get("message") or response_data.get("detail") or response_message
        error_code = response_data.get("code", error_code_num)
        try:
            error_code_num = int(error_code)
        except ValueError:
            error_code_string = error_code or error_code_string
    raise APIError(code=error_code_string, message=error_message + response_message, code_num=error_code_num) from exc


def exception_transformer_decorator(func):
    """A decorator wrap with transform_exception"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            return transform_exception(exc)

    return wrapper


def registry_i18n_hook(session: Session):
    """registry hook to bkapi client session, which will auto set Accept-Language"""

    def hook(request: Request):
        language = get_language()
        if language and not request.headers.get("Accept-Language"):
            request.headers["Accept-Language"] = language
        return request

    session.register_hook(HookEvent.REQUEST, hook)
