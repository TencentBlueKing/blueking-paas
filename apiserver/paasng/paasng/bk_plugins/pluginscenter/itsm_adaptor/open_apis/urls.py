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

from django.urls import path

from . import views

urlpatterns = [
    # 需要给 ITSM 后台回调的 Open API
    # 创建插件审批回调 API
    path(
        "open/api/itsm/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/",
        views.PluginCallBackApiViewSet.as_view({"post": "itsm_create_callback"}),
    ),
    # 发布流程中上线审批阶段回调 API
    path(
        "open/api/itsm/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/stages/<str:stage_id>/",
        views.PluginCallBackApiViewSet.as_view({"post": "itsm_stage_callback"}),
    ),
    # 可见范围修改回调 API
    path(
        "open/api/itsm/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/visible_range/",
        views.PluginCallBackApiViewSet.as_view({"post": "itsm_visible_range_callback"}),
    ),
]
