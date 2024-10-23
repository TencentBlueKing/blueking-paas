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
    # 获取指定 Region 可用场景 SaaS 模板列表
    re_path(
        r"^api/bkapps/(?P<tpl_type>[^/]+)/tmpls/$",
        views.TemplateViewSet.as_view({"get": "list_tmpls"}),
        name="api.templates.list_tmpls",
    ),
    # 获取指定 Region 可用场景 SaaS 模板列表
    re_path(
        r"^api/tmpls/(?P<tpl_type>[^/]+)/region/(?P<region>[^/]+)/$",
        views.RegionTemplateViewSet.as_view({"get": "list"}),
        name="api.templates.list",
    ),
    re_path(
        r"^api/tmpls/(?P<tpl_type>[^/]+)/region/(?P<region>[^/]+)/template/(?P<tpl_name>[^/]+)$",
        views.RegionTemplateViewSet.as_view({"get": "retrieve"}),
        name="api.templates.detail",
    ),
]
