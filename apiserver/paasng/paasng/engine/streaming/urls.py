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
from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        r'^streams/(?P<channel_id>[0-9a-f-]{32,36})$',
        views.StreamViewSet.as_view(dict(get="streaming")),
        name='streaming.stream',
    ),
    url(
        r'^streams/(?P<channel_id>[0-9a-f-]{32,36})/history_events$',
        views.StreamViewSet.as_view(dict(get="history_events")),
        name='streaming.stream.history_events',
    ),
    url(r'^streams/__debugger__$', views.StreamDebuggerView.as_view(), name='streaming.debugger'),
    url(r'^streams/__void__$', views.VoidViewset.as_view({'patch': 'patch_no_content'})),
    url(r'^streams/__void_with_content__$', views.VoidViewset.as_view({'patch': 'patch_with_content'})),
]
