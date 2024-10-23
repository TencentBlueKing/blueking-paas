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

from . import views

urlpatterns = [
    # 返回合并后的 swagger文档
    re_path(
        r"^docs/$",
        views.FullSwaggerConfigurationView.with_ui("swagger", cache_timeout=0),
        name="full-swagger-ui",
    ),
    re_path(
        r"^docs/swagger/$",
        views.FullSwaggerConfigurationView.with_ui("swagger", cache_timeout=0),
        name="full-swagger-ui",
    ),
    re_path(r"^docs/redoc/$", views.FullSwaggerConfigurationView.with_ui("redoc", cache_timeout=0), name="full-redoc"),
    re_path(
        r"^docs/swagger(?P<format>\.json|\.yaml)$",
        views.FullSwaggerConfigurationView.without_ui(cache_timeout=0),
        name="full-schema",
    ),
    re_path(
        r"^docs/auto/swagger(?P<format>\.json|\.yaml)$",
        views.schema_view.without_ui(cache_timeout=0),
        name="schema",
    ),
    re_path(r"^docs/auto/swagger/$", views.schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    re_path(r"^docs/auto/redoc/$", views.schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
