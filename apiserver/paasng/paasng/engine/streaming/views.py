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
from typing import List

from blue_krill.redis_tools.messaging import StreamChannelSubscriber
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.generic import View
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from paasng.engine.deploy.workflow import ServerSendEvent
from paasng.platform.core.storages.redisdb import get_default_redis
from paasng.utils.error_codes import error_codes
from paasng.utils.rate_limit.constants import UserAction
from paasng.utils.rate_limit.fixed_window import rate_limits_by_user
from paasng.utils.views import EventStreamRender

from .serializers import HistoryEventsQuerySLZ, StreamEventSLZ


class StreamViewSet(ViewSet):
    renderer_classes = [JSONRenderer, EventStreamRender]

    def get_subscriber(self, channel_id):
        subscriber = StreamChannelSubscriber(channel_id, redis_db=get_default_redis())
        channel_state = subscriber.get_channel_state()
        if channel_state == 'none':
            raise error_codes.CHANNEL_NOT_FOUND
        return subscriber

    @rate_limits_by_user(UserAction.FETCH_DEPLOY_LOG, window_size=60, threshold=10)
    def streaming(self, request, channel_id):
        subscriber = self.get_subscriber(channel_id)

        def resp():
            for data in subscriber.get_events():
                e = ServerSendEvent.from_raw(data)
                if e.is_internal:
                    continue

                for s in e.to_yield_str_list():
                    yield s

            for s in ServerSendEvent.to_eof_str_list():
                yield s

        return StreamingHttpResponse(resp(), content_type='text/event-stream')

    @swagger_auto_schema(query_serializer=HistoryEventsQuerySLZ, responses={200: StreamEventSLZ(many=True)})
    def history_events(self, request, channel_id):
        subscriber = self.get_subscriber(channel_id)
        slz = HistoryEventsQuerySLZ(data=request.query_params)
        slz.is_valid(True)

        last_event_id = slz.validated_data["last_event_id"]
        events = subscriber.get_history_events(last_event_id=last_event_id, ignore_special=False)
        return Response(data=StreamEventSLZ(events, many=True).data, content_type="application/json")


class StreamDebuggerView(View):
    def get(self, request):
        return render(request, 'streaming/debugger.html')


class VoidViewset(viewsets.ViewSet):
    permission_classes: List = []

    def patch_no_content(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch_with_content(self, request):
        return JsonResponse(status=status.HTTP_204_NO_CONTENT, data={})
