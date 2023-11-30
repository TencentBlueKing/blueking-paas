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

from paasng.plat_admin.system.views import (
    ClusterNamespaceInfoView,
    LessCodeSystemAPIViewSet,
    SysAddonsAPIViewSet,
    SysUniApplicationViewSet,
)
from paasng.utils.basic import make_app_pattern, re_path

urlpatterns = [
    # Query universal applications
    url(
        "sys/api/uni_applications/query/by_id/$",
        SysUniApplicationViewSet.as_view({"get": "query_by_id"}),
        name="sys.api.uni_applications.list_by_ids",
    ),
    url(
        "sys/api/uni_applications/query/by_username/$",
        SysUniApplicationViewSet.as_view({"get": "query_by_username"}),
        name="sys.api.uni_applications.list_by_username",
    ),
    # 分页查询应用基本信息
    url(
        "sys/api/uni_applications/list/minimal/$",
        SysUniApplicationViewSet.as_view({"get": "list_minimal_app"}),
        name="sys.api.uni_applications.list_minimal_app",
    ),
    url(
        "sys/api/bkapps/applications/(?P<code>[^/]+)/cluster_namespaces/$",
        ClusterNamespaceInfoView.as_view({"get": "list_by_app_code"}),
        name="sys.api.applications.cluster_namespace.list_by_app_code",
    ),
    re_path(
        make_app_pattern(suffix="/lesscode/query_db_credentials", prefix="sys/api/bkapps/applications/"),
        LessCodeSystemAPIViewSet.as_view({"get": "query_db_credentials"}),
        name="sys.api.lesscode.query_db_credentials",
    ),
    re_path(
        make_app_pattern(
            suffix="/lesscode/bind_db_service", prefix="sys/api/bkapps/applications/", include_envs=False
        ),
        LessCodeSystemAPIViewSet.as_view({"post": "bind_db_service"}),
        name="sys.api.lesscode.bind_db_service",
    ),
    re_path(
        make_app_pattern(suffix="/addons/(?P<service_name>[^/]+)/", prefix="sys/api/bkapps/applications/"),
        SysAddonsAPIViewSet.as_view({"get": "query_credentials", "post": "provision_service"}),
        name="sys.api.applications.addons",
    ),
    re_path(
        make_app_pattern(suffix="/addons/", prefix="sys/api/bkapps/applications/"),
        SysAddonsAPIViewSet.as_view({"get": "list_services"}),
        name="sys.api.applications.list_addons",
    ),
    re_path(
        make_app_pattern(
            suffix="/services/(?P<service_id>[0-9a-f-]{32,36})/specs/",
            include_envs=False,
            prefix="sys/api/bkapps/applications/",
        ),
        SysAddonsAPIViewSet.as_view({"get": "retrieve_specs"}),
        name="sys.api.applications.retrieve_specs",
    ),
]
