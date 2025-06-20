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

from django.urls import re_path

from .views import SourceTypeSpecViewSet

urlpatterns = [
    re_path(
        r"^api/plat_mgt/sourcectl/source_type_spec/$",
        SourceTypeSpecViewSet.as_view({"get": "list", "post": "create"}),
        name="plat_mgt.sourcectl.source_type_spec.list_create",
    ),
    re_path(
        r"^api/plat_mgt/sourcectl/source_type_spec/default_configs_templates/$",
        SourceTypeSpecViewSet.as_view({"get": "get_default_configs_templates"}),
        name="plat_mgt.sourcectl.source_type_spec.default_configs_templates",
    ),
    re_path(
        r"^api/plat_mgt/sourcectl/spec_cls_choices/$",
        SourceTypeSpecViewSet.as_view({"get": "get_spec_cls_choices"}),
        name="plat_mgt.sourcectl.source_type_spec.spec_cls_choices",
    ),
    re_path(
        r"^api/plat_mgt/sourcectl/source_type_spec/(?P<pk>[^/]+)/$",
        SourceTypeSpecViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="plat_mgt.sourcectl.source_type_spec.retrieve_update_destroy",
    ),
]
