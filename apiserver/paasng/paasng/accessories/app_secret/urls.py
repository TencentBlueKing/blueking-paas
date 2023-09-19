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

from paasng.accessories.app_secret import views

urlpatterns = [
    url(
        r'^api/bkapps/applications/(?P<code>[^/]+)/secrets/$',
        views.BkAuthSecretViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='api.app_secret.secrets',
    ),
    url(
        r'^api/bkapps/applications/(?P<code>[^/]+)/secrets/(?P<bk_app_secret_id>\d+)/$',
        views.BkAuthSecretViewSet.as_view({'post': 'toggle', 'delete': 'delete'}),
        name='api.app_secret.secret',
    ),
    # 验证验证码查看密钥详情
    url(
        r'^api/bkapps/applications/(?P<code>[^/]+)/secret_verification/(?P<bk_app_secret_id>\d+)/$',
        views.BkAuthSecretViewSet.as_view({'post': 'view_secret_detail'}),
        name='api.app_secret.secret_verification',
    ),
    url(
        r'^api/bkapps/applications/(?P<code>[^/]+)/default_secret/$',
        views.BkAppSecretInEnvVaViewSet.as_view({'get': 'get_default_secret', 'post': 'rotate_default_secret'}),
        name='api.app_secret.default_secret',
    ),
    url(
        r'^api/bkapps/applications/(?P<code>[^/]+)/deployed_secret/$',
        views.BkAppSecretInEnvVaViewSet.as_view(
            {
                'get': 'get_deployed_secret',
            }
        ),
        name='api.app_secret.deployed_secret',
    ),
]
