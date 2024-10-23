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
    re_path(
        r"^api/document/search/$",
        views.MixDocumentSearch.as_view({"get": "search"}),
        name="document-search",
    ),
    # API: search results in each categories
    re_path(
        r"^api/search/applications/$",
        views.ApplicationsSearchViewset.as_view({"get": "search"}),
        name="search.applications",
    ),
    re_path(
        r"^api/search/bk_docs/$",
        views.BkDocsSearchViewset.as_view({"get": "search"}),
        name="search.bk_docs",
    ),
]

try:
    from .urls_ext import urlpatterns as urlpatterns_ext

    urlpatterns += urlpatterns_ext
except ImportError:
    pass
