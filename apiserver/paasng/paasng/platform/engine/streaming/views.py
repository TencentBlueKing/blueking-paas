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
from contextlib import closing

from blue_krill.redis_tools.messaging import StreamChannelSubscriber
from django.http import StreamingHttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.utils.ansi import strip_ansi
from paasng.platform.engine.workflow import ServerSendEvent
from paasng.utils.error_codes import error_codes
from paasng.utils.rate_limit.constants import UserAction
from paasng.utils.rate_limit.fixed_window import rate_limits_by_user
from paasng.utils.views import EventStreamRender

from .serializers import HistoryEventsQuerySLZ, StreamEventSLZ, StreamingQuerySLZ


class StreamViewSet(ViewSet):
    """提供一个通用的事件流接口，供构建日志等场景使用。

    INFO: 虽然 streaming 的 API 最开始被设计为通用的底层接口，但目前仅被构建日志所使用，所以这个接口可以被等同
    于一个获取构建/部署日志的接口。另外，为了安全，本 API 直接针对 channel_id -> Deployment -> App -> Check
    Permission 的链路做了鉴权，以避免随机碰撞访问。
    """

    renderer_classes = [JSONRenderer, EventStreamRender]
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def get_subscriber(self, request, channel_id):
        # Do permission check to avoid user viewing logs of others by passing a random channel_id
        app = _get_channel_deployment(channel_id).app_environment.module.application
        self.check_object_permissions(request, app)
        return _make_subscriber(channel_id)

    @rate_limits_by_user(UserAction.FETCH_DEPLOY_LOG, window_size=60, threshold=10)
    @swagger_auto_schema(
        query_serializer=StreamingQuerySLZ,
        responses={200: StreamEventSLZ(many=True)},
        tags=["streams"],
    )
    def streaming(self, request, channel_id):
        query_serializer = StreamingQuerySLZ(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        subscriber = self.get_subscriber(request, channel_id)
        include_ansi_codes = query_serializer.validated_data["include_ansi_codes"]

        def process_event_line(line: str) -> str:
            """处理事件行，过滤掉 ANSI 转义序列"""
            if include_ansi_codes:
                return line

            if not line.startswith("data: "):
                return line
            line = line.removesuffix("\n\n")

            content = line[6:]
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return line + "\n\n"

            if "line" not in data:
                return line + "\n\n"
            data["line"] = strip_ansi(data["line"])
            return line[:6] + json.dumps(data) + "\n\n"

        def resp():
            with closing(subscriber):
                for data in subscriber.get_events():
                    e = ServerSendEvent.from_raw(data)
                    if e.is_internal:
                        continue

                    yield from (process_event_line(line) for line in e.to_yield_str_list())

                for s in ServerSendEvent.to_eof_str_list():
                    yield s

        return StreamingHttpResponse(resp(), content_type="text/event-stream")

    @swagger_auto_schema(query_serializer=HistoryEventsQuerySLZ, responses={200: StreamEventSLZ(many=True)})
    def history_events(self, request, channel_id):
        slz = HistoryEventsQuerySLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        subscriber = self.get_subscriber(request, channel_id)
        return _render_history_events(subscriber, slz.validated_data["last_event_id"])


class SysStreamViewSet(ViewSet):
    """应用态事件流接口，目前仅支持 AIDEV 获取 AI Agent 应用的部署日志。"""

    permission_classes = [sysapi_client_perm_class(ClientAction.DEPLOY_AI_AGENT_APP)]

    @swagger_auto_schema(
        query_serializer=HistoryEventsQuerySLZ, responses={200: StreamEventSLZ(many=True)}, tags=["streams"]
    )
    def history_events(self, request, channel_id):
        """应用态获取部署日志历史事件，仅允许查询 AI Agent 应用的部署。"""
        slz = HistoryEventsQuerySLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        app = _get_channel_deployment(channel_id).app_environment.module.application
        if not app.is_ai_agent_app:
            raise error_codes.AI_AGENT_APP_REQUIRED

        subscriber = _make_subscriber(channel_id)
        return _render_history_events(subscriber, slz.validated_data["last_event_id"])


def _get_channel_deployment(channel_id: str) -> Deployment:
    """将 channel_id 作为一个有效的 Deployment ID 获取部署对象，用于后续鉴权"""
    try:
        return Deployment.objects.get(pk=channel_id)
    except Deployment.DoesNotExist:
        # 阻挡所有非有效 Deployment 的 channel_id
        raise error_codes.CANNOT_GET_DEPLOYMENT


def _make_subscriber(channel_id: str) -> StreamChannelSubscriber:
    subscriber = StreamChannelSubscriber(channel_id, redis_db=get_default_redis())
    channel_state = subscriber.get_channel_state()
    if channel_state == "none":
        raise error_codes.CHANNEL_NOT_FOUND
    return subscriber


def _render_history_events(subscriber: StreamChannelSubscriber, last_event_id: int) -> Response:
    with closing(subscriber):
        events = subscriber.get_history_events(last_event_id=last_event_id, ignore_special=False)
    return Response(data=StreamEventSLZ(events, many=True).data, content_type="application/json")
