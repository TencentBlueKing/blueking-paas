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

"""应用态 (系统 API) 事件流视图

这些接口注册在 `sys/api/` 路径下, 仅供 AIDEV / AppSpark 等固定的系统调用, 鉴权依赖 sysapi_client.
"""

from drf_yasg.utils import swagger_auto_schema
from rest_framework.viewsets import ViewSet

from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.platform.applications.mixins import SysManagedAppInPathMixin
from paasng.platform.engine.streaming.serializers import HistoryEventsQuerySLZ, StreamEventSLZ

from .api import get_channel_deployment, make_subscriber, render_history_events


class SysStreamViewSet(ViewSet, SysManagedAppInPathMixin):
    """应用态事件流接口：AIDEV 获取 AI Agent 应用、AppSpark 获取 AppSpark 应用的部署日志。"""

    permission_classes = [sysapi_client_perm_class(ClientAction.DEPLOY_APPLICATIONS)]

    @swagger_auto_schema(
        query_serializer=HistoryEventsQuerySLZ, responses={200: StreamEventSLZ(many=True)}, tags=["streams"]
    )
    def history_events(self, request, channel_id):
        """应用态获取部署日志历史事件，只允许查询调用方管理的应用的部署。"""
        slz = HistoryEventsQuerySLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        # 路径里只有部署 ID，没有应用和模块，所以按部署所在的环境校验归属。
        # 同一个权限动作 AIDEV 和 AppSpark 都有，漏掉这一步就能读到对方应用的日志
        self.ensure_env_managed_by_client(get_channel_deployment(channel_id).app_environment)

        subscriber = make_subscriber(channel_id)
        return render_history_events(subscriber, slz.validated_data["last_event_id"])
