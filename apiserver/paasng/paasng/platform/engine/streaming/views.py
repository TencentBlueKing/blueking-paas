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
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.workflow import ServerSendEvent
from paasng.utils.error_codes import error_codes
from paasng.utils.rate_limit.constants import UserAction
from paasng.utils.rate_limit.fixed_window import rate_limits_by_user
from paasng.utils.views import EventStreamRender

from .serializers import HistoryEventsQuerySLZ, StreamEventSLZ


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
        self._check_channel_perm_as_deploy(request, channel_id)

        subscriber = StreamChannelSubscriber(channel_id, redis_db=get_default_redis())
        channel_state = subscriber.get_channel_state()
        if channel_state == "none":
            raise error_codes.CHANNEL_NOT_FOUND
        return subscriber

    def _check_channel_perm_as_deploy(self, request, channel_id):
        """将 channel_id 作为一个有效的 Deployment ID，并进行权限校验"""
        try:
            deployment = Deployment.objects.get(pk=channel_id)
        except Deployment.DoesNotExist:
            # 阻挡所有非有效 Deployment 的 channel_id
            raise error_codes.CANNOT_GET_DEPLOYMENT

        app = deployment.app_environment.module.application
        self.check_object_permissions(request, app)

    @rate_limits_by_user(UserAction.FETCH_DEPLOY_LOG, window_size=60, threshold=10)
    def streaming(self, request, channel_id):
        subscriber = self.get_subscriber(request, channel_id)

        def resp():
            with closing(subscriber):
                for data in subscriber.get_events():
                    e = ServerSendEvent.from_raw(data)
                    if e.is_internal:
                        continue

                    for s in e.to_yield_str_list():
                        yield s

                for s in ServerSendEvent.to_eof_str_list():
                    yield s

        return StreamingHttpResponse(resp(), content_type="text/event-stream")

    @swagger_auto_schema(query_serializer=HistoryEventsQuerySLZ, responses={200: StreamEventSLZ(many=True)})
    def history_events(self, request, channel_id):
        slz = HistoryEventsQuerySLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        subscriber = self.get_subscriber(request, channel_id)

        with closing(subscriber):
            last_event_id = slz.validated_data["last_event_id"]
            events = subscriber.get_history_events(last_event_id=last_event_id, ignore_special=False)

        return Response(data=StreamEventSLZ(events, many=True).data, content_type="application/json")
