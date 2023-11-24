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
from paasng.utils.basic import make_app_pattern, re_path

from . import views

urlpatterns = [
    re_path(
        make_app_pattern(r"/exposed_url_type/$", include_envs=False),
        views.ExposedURLTypeViewset.as_view({"put": "update"}),
        name="api.entrance.exposed_url_type",
    ),
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/default_entrance/$",
        views.ApplicationAvailableAddressViewset.as_view({"get": "list_default_entrance"}),
        name="api.entrance.default_entrance",
    ),
    re_path(
        make_app_pattern(r"/default_entrance/$", include_envs=False),
        views.ApplicationAvailableAddressViewset.as_view({"get": "list_module_default_entrances"}),
        name="api.entrance.module.default_entrances",
    ),
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/custom_domain_entrance/$",
        views.ApplicationAvailableAddressViewset.as_view({"get": "list_custom_domain_entrance"}),
        name="api.entrance.custom_domain_entrance",
    ),
    re_path(
        make_app_pattern(r"/root_domains/$", include_envs=False),
        views.ModuleRootDomainsViewSet.as_view({"get": "list_root_domains"}),
        name="api.entrance.module.root_domain",
    ),
    re_path(
        make_app_pattern(r"/preferred_root_domain/$", include_envs=False),
        views.ModuleRootDomainsViewSet.as_view({"put": "update_preferred_root_domain"}),
        name="api.entrance.module.preferred_root_domain",
    ),
]
