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
        r"^api/market/tags/(?P<id>[^/]+)$",
        views.TagViewSet.as_view({"get": "retrieve"}),
        name="api.market.tags.detail",
    ),
    re_path(r"^api/market/tags$", views.TagViewSet.as_view({"get": "list"}), name="api.market.tags"),
    # NOTE: put/post 等资源必须以 / 为末尾
    # TODO: 等前端将 api 统一成带斜杠时, 去掉 `?`
    re_path(
        r"^api/market/products/(?P<code>[^/]+)/state/?$",
        views.ProductStateViewSet.as_view({"get": "retrieve", "put": "update"}),
        name="api.market.products.state",
    ),
    # NOTE: put/post 等资源必须以 / 为末尾
    # TODO: 等前端将 api 统一成带斜杠时, 去掉 `?`
    re_path(
        r"^api/market/products/(?P<code>[^/]+)/?$",
        views.ProductCombinedViewSet.as_view({"get": "retrieve", "put": "update"}),
        name="api.market.products.detail",
    ),
    # NOTE: put/post 等资源必须以 / 为末尾
    # TODO: 等前端将 api 统一成带斜杠时, 去掉 `?`
    re_path(
        r"^api/market/products/?$",
        views.ProductCreateViewSet.as_view({"post": "create", "get": "list"}),
        name="api.market.products.list",
    ),
    re_path(
        r"^api/market/corp_products/$",
        views.CorpProductViewSet.as_view({"get": "list"}),
        name="api.market.corp_products",
    ),
]

urlpatterns += [
    re_path(
        r"^api/market/applications/(?P<code>[^/]+)/switch/$",
        views.MarketConfigViewSet.as_view({"post": "switch"}),
        name="api.market.application.switch",
    ),
    # Deprecated
    re_path(
        r"^api/market/applications/(?P<code>[^/]+)/config/$",
        views.MarketConfigViewSet.as_view({"get": "retrieve", "put": "update"}),
        name="api.market.application.config",
    ),
    re_path(
        r"^api/market/applications/(?P<code>[^/]+)/publish/preparations/$",
        views.PublishViewSet.as_view({"get": "check_preparations"}),
        name="api.market.application.publish.preparations",
    ),
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/entrances/market/$",
        views.MarketConfigViewSet.as_view({"post": "set_entrance"}),
        name="api.applications.entrances.market_entrance",
    ),
]
