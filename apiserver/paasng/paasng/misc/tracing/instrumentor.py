# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Collection, Optional

from django.conf import settings
from opentelemetry.instrumentation import dbapi
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.trace import Span, Status, StatusCode
from requests.models import Response


def requests_callback(span: Span, response: Optional[Response]):
    """
    处理蓝鲸标准协议响应
    """
    # requests 请求异常, 例如访问超时等
    if response is None:
        return

    # 并非所有返回内容都是 json 格式的, 因此需要根据返回头进行判断, 避免处理二进制格式的内容
    if response.headers.get("Content-Type") != "application/json":
        return

    try:
        json_result = response.json()
    except Exception:  # pylint: disable=broad-except
        return

    if not isinstance(json_result, dict):
        return

    # NOTE: esb got a result, but apigateway got not result
    code = json_result.get("code", 0)
    try:
        code = int(code)
    except Exception:  # pylint: disable=broad-except
        pass
    span.set_attribute("result_code", code)
    if code in [0, "0", "00"]:
        span.set_status(Status(StatusCode.OK))
    else:
        span.set_status(Status(StatusCode.ERROR))

    span.set_attribute("result_message", json_result.get("message", ""))

    errors = str(json_result.get("errors", ""))
    if errors:
        span.set_attribute("result_errors", errors)

    request_id = (
        # new esb and apigateway
        response.headers.get("x-bkapi-request-id")
        # app engine api
        or response.headers.get(settings.REQUEST_ID_HEADER_KEY)
        # old esb
        or json_result.get("request_id", "")
    )
    if request_id:
        span.set_attribute("request_id", request_id)


def django_response_hook(span: Span, request, response):
    """
    处理 PaasNG Django 响应
    """
    if response.status_code == 200:
        span.set_status(Status(StatusCode.OK))
    else:
        span.set_status(Status(StatusCode.ERROR))

    span.set_attribute("request_id", request.request_id)
    span.set_attribute("reason_phrase", response.reason_phrase)


class BKAppInstrumentor(BaseInstrumentor):
    def instrumentation_dependencies(self) -> Collection[str]:
        return []

    def _instrument(self, **kwargs):
        LoggingInstrumentor().instrument()
        RequestsInstrumentor().instrument(span_callback=requests_callback)
        DjangoInstrumentor().instrument(response_hook=django_response_hook)
        RedisInstrumentor().instrument()
        CeleryInstrumentor().instrument()

        if getattr(settings, "OTEL_INSTRUMENT_DB_API", False):
            import MySQLdb

            dbapi.wrap_connect(
                __name__,
                MySQLdb,
                "connect",
                "mysql",
                {"database": "db", "port": "port", "host": "host", "user": "user"},
            )

    def _uninstrument(self, **kwargs):
        for instrumentor in self.instrumentors:
            instrumentor.uninstrument()
