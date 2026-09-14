# -*- coding: utf-8 -*-
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

import json
import logging
from itertools import islice
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, TypeVar

from bkapi_client_core.exceptions import APIGatewayResponseError, HTTPResponseError
from django.conf import settings

from paasng.core.tenant.constants import API_HERDER_TENANT_ID
from paasng.infras.iam.base.constants import V4_BATCH_OPERATION_LIMIT, V4_LIST_PAGE_SIZE_LIMIT, V4_OPERATOR_HEADER
from paasng.infras.iam.constants import DEFAULT_PAGE
from paasng.infras.iam.exceptions import BKIAMApiError, BKIAMApiHTTPError, BKIAMGatewayServiceError
from paasng.infras.iam.v4.apigw.client import Client
from paasng.infras.iam.v4.apigw.client import Group as BKIAMV4Group

logger = logging.getLogger(__name__)

T = TypeVar("T")


def batched(items: Iterable[T], batch_size: int) -> Iterator[List[T]]:
    """将条目切分为若干批，每批不超过 batch_size 条"""
    if batch_size <= 0:
        raise ValueError(f"batch_size must be positive, got {batch_size}")

    iterator = iter(items)
    while batch := list(islice(iterator, batch_size)):
        yield batch


class BKIAMV4BaseClient:
    """权限中心 V4 客户端基座

    各业务实现继承本类，通过 `self.client` 访问网关 Operation，并经 `call` / `paginate` /
    `call_in_batches` 发起调用，以复用统一的 header 注入、翻页、分批与错误处理逻辑。

    :param tenant_id: 租户标识，逐请求透传
    :param operator: 操作人。V4 写操作要求携带该标识，为空时使用 BK_APP_CODE
    """

    def __init__(self, tenant_id: str, operator: Optional[str] = None):
        self._client = Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_IAM_V4_APIGW_SERVICE_STAGE)
        self.tenant_id = tenant_id
        self.operator = operator or settings.BK_APP_CODE
        self.client: BKIAMV4Group = self._client.api

    def call(
        self,
        operation: Callable[..., Dict],
        *,
        path_params: Optional[Dict] = None,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        for_write: bool = False,
    ) -> Dict:
        """发起一次 V4 接口调用

        :param for_write: 是否为写操作。写操作会额外注入操作人 header
        :raises BKIAMApiHTTPError: 权限中心返回非 2xx 状态码
        :raises BKIAMApiError: 权限中心返回业务错误
        :raises BKIAMGatewayServiceError: 网关不可达、超时或返回无法解析的内容
        """
        kwargs: Dict[str, Any] = {"headers": self._prepare_headers(for_write=for_write)}
        if path_params is not None:
            kwargs["path_params"] = path_params
        if params is not None:
            kwargs["params"] = params
        if data is not None:
            kwargs["data"] = data

        name = getattr(operation, "name", repr(operation))
        try:
            resp = operation(**kwargs)
        except HTTPResponseError as e:
            raise BKIAMApiHTTPError(
                f"request bkiam api {name} failed: {e}",
                status_code=e.response_status_code,
                request_id=self._extract_request_id(e),
            ) from e
        except APIGatewayResponseError as e:
            # 网关不可达或超时。不做默认放行，由调用方决定重试与告警
            raise BKIAMGatewayServiceError(f"request bkiam api {name} error, detail: {e}") from e

        self._validate_resp(resp, name)
        return {} if resp in (None, "") else resp

    def paginate(
        self,
        operation: Callable[..., Dict],
        *,
        path_params: Optional[Dict] = None,
        params: Optional[Dict] = None,
        page_size: int = V4_LIST_PAGE_SIZE_LIMIT,
    ) -> Iterator[Dict]:
        """逐页拉取列表接口的全部结果，直到取完为止，不静默截断"""
        if page_size > V4_LIST_PAGE_SIZE_LIMIT:
            raise ValueError(f"page_size {page_size} exceeds the bkiam limit {V4_LIST_PAGE_SIZE_LIMIT}")

        page, fetched = DEFAULT_PAGE, 0
        while True:
            resp = self.call(
                operation,
                path_params=path_params,
                params={**(params or {}), "page": page, "page_size": page_size},
            )
            data = resp.get("data") or {}
            results = data.get("results") or []
            yield from results

            fetched += len(results)
            # 本页未取满即为最后一页，无需再发起一次必然为空的请求
            if len(results) < page_size:
                return

            total = data.get("count")
            if total is not None and fetched >= total:
                return

            page += 1

    def call_in_batches(
        self,
        operation: Callable[..., Dict],
        items: Iterable[T],
        build_data: Callable[[List[T]], Any],
        *,
        path_params: Optional[Dict] = None,
        batch_size: int = V4_BATCH_OPERATION_LIMIT,
        for_write: bool = True,
    ) -> List[Dict]:
        """将超出单次上限的条目自动分批调用

        :param build_data: 由一批条目构造请求体
        :returns: 各批次的响应，由调用方按业务语义合并
        """
        if batch_size > V4_BATCH_OPERATION_LIMIT:
            raise ValueError(f"batch_size {batch_size} exceeds the bkiam limit {V4_BATCH_OPERATION_LIMIT}")

        return [
            self.call(operation, path_params=path_params, data=build_data(batch), for_write=for_write)
            for batch in batched(items, batch_size)
        ]

    def _prepare_headers(self, for_write: bool = False) -> Dict[str, str]:
        headers = {
            "x-bkapi-authorization": json.dumps(
                {
                    "bk_app_code": settings.IAM_APP_CODE,
                    "bk_app_secret": settings.IAM_APP_SECRET,
                }
            ),
            API_HERDER_TENANT_ID: self.tenant_id,
        }
        if for_write:
            headers[V4_OPERATOR_HEADER] = self.operator
        return headers

    @staticmethod
    def _validate_resp(resp: Dict, operation_name: str):
        """校验响应内容

        note: V4 成功响应体中没有 code 字段，错误主要经 HTTP 状态码表达。此处兼容
            网关层或后续版本可能返回的 code 字段，非 0 时按业务错误处理
        """
        # 204 No Content：更新/删除成功时没有响应体
        if resp in (None, ""):
            return

        if not isinstance(resp, dict):
            raise BKIAMGatewayServiceError(f"request bkiam api {operation_name} got unexpected response: {resp!r}")

        code = resp.get("code")
        if code is None or code == 0:
            return

        request_id = resp.get("request_id")
        message = resp.get("message") or ""
        logger.error(
            "request bkiam api %s failed, code: %s, message: %s, request_id: %s",
            operation_name,
            code,
            message,
            request_id,
        )
        raise BKIAMApiError(message, code, request_id)

    @staticmethod
    def _extract_request_id(exc: HTTPResponseError) -> Optional[str]:
        """从错误响应中提取权限中心的 request_id，用于跨系统排查

        网关会将 request_id 放在响应头中并由 SDK 解析，权限中心则将其放在响应体里，
        两处都取一遍以覆盖网关层与权限中心自身的报错
        """
        if exc.request_id:
            return exc.request_id

        if exc.response is None:
            return None

        try:
            return (exc.response.json() or {}).get("request_id")
        except (ValueError, AttributeError):
            # 响应体不是 JSON，或不是对象结构
            return None
