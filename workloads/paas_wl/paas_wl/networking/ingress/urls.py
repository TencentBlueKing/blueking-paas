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
from django.urls import re_path

from paas_wl.utils import text

from . import views

PVAR_SERVICE_NAME = '(?P<service_name>[a-z0-9-]+)'

urlpatterns = [
    # Manage the default ingress rule
    re_path(
        f'^regions/{text.PVAR_REGION}/apps/{text.PVAR_NAME}/proc_ingresses/actions/sync$',
        views.ProcIngressViewSet.as_view({'post': 'sync'}),
    ),
    re_path(
        f'^regions/{text.PVAR_REGION}/apps/{text.PVAR_NAME}/domains/$',
        views.AppDomainViewSet.as_view({'get': 'list', 'put': 'update'}),
    ),
    # Shared certificates
    re_path(
        '^app_certs/shared/$',
        views.AppDomainSharedCertsViewSet.as_view({'post': 'create', 'get': 'list'}),
    ),
    re_path(
        '^app_certs/shared/(?P<name>[a-zA-Z0-9_-]+)$',
        views.AppDomainSharedCertsViewSet.as_view({'get': 'retrieve', 'post': 'update', 'delete': 'destroy'}),
    ),
    # Subpath
    re_path(
        f'^regions/{text.PVAR_REGION}/apps/{text.PVAR_NAME}/subpaths/$',
        views.AppSubpathViewSet.as_view({'get': 'list', 'put': 'update'}),
    ),
]
