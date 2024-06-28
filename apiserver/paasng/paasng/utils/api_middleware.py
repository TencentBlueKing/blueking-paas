# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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
import time
from typing import Dict

import redis
from django.conf import settings
from django.http.response import HttpResponse
from django.urls import resolve
from django.utils.encoding import force_text

from paasng.misc.metrics import API_VISITED_COUNTER, API_VISITED_TIME_CONSUME_HISTOGRAM
from paasng.utils.basic import get_client_ip

logger = logging.getLogger(__name__)


class ApiLogMiddleware:
    project_code = "bk-paas-ng"
    index_name = "log-paas_ng-{date}"

    # max log size is 1K
    max_content_size = 1024
    doc_type = "api"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.start_time = time.time()
        response = self.get_response(request)
        msecs_cost = int((time.time() - request.start_time) * 1000)

        try:
            data = dict(
                method=request.method, endpoint=resolve(request.path_info).url_name, status=response.status_code
            )
        except Exception:
            data = dict(method=request.method, endpoint="", status=response.status_code)
            logger.warning(f"api<{request.path}> resolve failed")

        API_VISITED_COUNTER.labels(**data).inc()
        API_VISITED_TIME_CONSUME_HISTOGRAM.labels(**data).observe(msecs_cost)

        try:
            api_data = self.get_api_data(request, response)
            self.save_data(api_data)
        except Exception as error:
            if not settings.DEBUG:
                logger.warning("%s api log error: %s", request, error)

        return response

    def truncate(self, content):
        if len(content) > self.max_content_size:
            content = content[: self.max_content_size] + "...(truncated)"
        return content

    def get_api_data(self, request, response):
        if request.method in ["OPTIONS"]:
            return None

        username = request.user.username
        user_id = request.user.get_username()
        # request use body
        # data = self.truncate(json.dumps(request.POST.dict()))

        # django.http.response.StreamingHttpResponse just ignore
        if isinstance(response, HttpResponse):
            content = self.truncate(force_text(response.content))
        else:
            content = ""

        data = {
            "project_code": self.project_code,
            "request_id": request.META.get("request_id", ""),
            "username": username,
            "user_id": user_id,
            "client_ip": get_client_ip(request),
            "method": request.method,
            "path": request.path,
            "params": json.dumps(request.GET.dict()),
            "msecs_cost": int((time.time() - request.start_time) * 1000),
            "status": response.status_code,
            "response_content": content,
            "type": self.doc_type,
        }
        return data

    def save_data(self, data):
        if not data:
            return

        save_redis(data)


_redis_client = None


def save_redis(doc: Dict):
    """
    保存日志数据到 Redis 队列
    """
    handler_config = settings.PAAS_API_LOG_REDIS_HANDLER
    if not handler_config.get("enabled", False):
        return

    # Connect to redis and save the connection pool afterwards
    global _redis_client
    if _redis_client is None:
        connection_options = getattr(settings, "REDIS_CONNECTION_OPTIONS", {})
        # TODO ee 版本如果开启, 再支持 sentinel 模式. 届时 PAAS_API_LOG_REDIS_HANDLER 参数也要适配调整
        _redis_client = redis.from_url(handler_config["url"], **connection_options)

    doc["tags"] = handler_config.get("tags", [])
    try:
        data = json.dumps(doc)
    except Exception as e:
        logger.warning(f"unable to dump api log data: {e}")
        return

    _redis_client.rpush(handler_config["queue_name"], data)
