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
    url(r'^api/user/$', views.UserInfoViewSet.as_view(), name='api.accounts.user'),
    url(
        r'^api/accounts/feature_flags/$',
        views.AccountFeatureFlagViewSet.as_view({"get": "list"}),
        name='api.accounts.feature_flags',
    ),
    url(r'^api/accounts/userinfo/$', views.UserInfoViewSet.as_view(), name='api.accounts.userinfo'),
    url(
        r'^api/accounts/verification/generation/$',
        views.UserVerificationGenerationView.as_view(),
        name='api.accounts.verification.generation',
    ),
    url(
        r'^api/accounts/verification/validation/$',
        views.UserVerificationValidationView.as_view(),
        name='api.accounts.verification.validation',
    ),
    url(
        r'^api/accounts/oauth/token/$',
        views.OauthTokenViewSet.as_view({"get": "fetch_paasv3cli_token"}),
        name='api.accounts.oauth.token',
    ),
    url(r'^api/oauth/backends/$', views.Oauth2BackendsViewSet.as_view({"get": "list"})),
    url(
        r'^api/oauth/backends/(?P<backend>[^/]+)/(?P<pk>[^/]+)/$',
        views.Oauth2BackendsViewSet.as_view({"delete": "disconnect"}),
    ),
    # for provider call back
    url(r'^api/oauth/complete/(?P<backend>[^/]+)/?$', views.Oauth2BackendsViewSet.as_view({"get": "bind"})),
]
