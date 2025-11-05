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


from paasng.utils.basic import re_path

from .views import SmartBuilderViewSet

urlpatterns = [
    re_path(
        r"^api/tools/s-mart/upload/$",
        SmartBuilderViewSet.as_view({"post": "upload"}),
        name="api.tools.s-mart.upload",
    ),
    re_path(
        r"^api/tools/s-mart/build/$",
        SmartBuilderViewSet.as_view({"post": "build_smart"}),
        name="api.tools.s-mart.build",
    ),
    re_path(
        r"^api/tools/s-mart/build_records/$",
        SmartBuilderViewSet.as_view({"get": "list_history"}),
        name="api.tools.s-mart.build_records",
    ),
    re_path(
        r"^api/tools/s-mart/build_records/(?P<uuid>[0-9a-f-]{36})/logs/$",
        SmartBuilderViewSet.as_view({"get": "get_history_logs"}),
        name="api.tools.s-mart.build_records.logs",
    ),
    re_path(
        r"^api/tools/s-mart/build_records/(?P<uuid>[0-9a-f-]{36})/logs/download/$",
        SmartBuilderViewSet.as_view({"get": "download_history_logs"}),
        name="api.tools.s-mart.build_records.logs.download",
    ),
    re_path(
        r"^api/tools/s-mart/build_records/(?P<uuid>[0-9a-f-]{36})/artifact/download/$",
        SmartBuilderViewSet.as_view({"get": "download_artifact"}),
        name="api.tools.s-mart.build_records.artifact.download",
    ),
]
