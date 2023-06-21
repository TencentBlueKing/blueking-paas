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

from paasng.utils.basic import make_app_pattern, re_path

from . import views

urlpatterns = [
    url(
        r'^api/bkapps/applications/(?P<code>[^/]+)/modules/$',
        views.ModuleViewSet.as_view({'get': 'list', 'post': 'create'}),
        name="modules",
    ),
    url(
        r'^api/bkapps/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/$',
        views.ModuleViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
        name="module.actions",
    ),
    re_path(
        make_app_pattern('/set_default/$', include_envs=False),
        views.ModuleViewSet.as_view({'post': 'set_as_default'}),
        name="module.set_default",
    ),
    url(
        r'^api/bkapps/cloud-native/(?P<code>[^/]+)/modules/$',
        views.ModuleViewSet.as_view({'post': 'create_cloud_native_module'}),
        name='module.create.cloud_native',
    ),
    # BuildPack Runtime(Deprecated: using ModuleBuildConfigViewSet)
    url(
        r'^api/bkapps/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/runtime/list/$',
        views.ModuleRuntimeViewSet.as_view({'get': 'list_available'}),
        name='api.modules.runtime.available_list',
    ),
    url(
        r'^api/bkapps/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/runtime/$',
        views.ModuleRuntimeViewSet.as_view({'get': 'retrieve', 'post': 'bind'}),
        name='api.modules.runtime',
    ),
    re_path(
        make_app_pattern("/runtime/overview", include_envs=False),
        views.ModuleRuntimeOverviewView.as_view(),
        name="api.modules.deployment.meta_info",
    ),
    # BuildConfig
    re_path(
        make_app_pattern("/build_config/$", include_envs=False),
        views.ModuleBuildConfigViewSet.as_view({"get": "retrieve", "post": "modify"}),
        name="api.modules.build_config",
    ),
    url(
        make_app_pattern("/bp_runtimes/$", include_envs=False),
        views.ModuleBuildConfigViewSet.as_view({'get': 'list_available_bp_runtimes'}),
        name='api.modules.bp_runtime.available_list',
    ),
    # DeployConfig
    re_path(
        make_app_pattern("/deploy_config/$", include_envs=False),
        views.ModuleDeployConfigViewSet.as_view({"get": "retrieve"}),
        name="api.modules.deploy_config",
    ),
    re_path(
        make_app_pattern("/deploy_config/hooks/$", include_envs=False),
        views.ModuleDeployConfigViewSet.as_view({"post": "upsert_hook"}),
        name="api.modules.deploy_config.hooks.upsert",
    ),
    re_path(
        make_app_pattern(r"/deploy_config/hooks/(?P<type_>[^/]+)/disable/$", include_envs=False),
        views.ModuleDeployConfigViewSet.as_view({"put": "disable_hook"}),
        name="api.modules.deploy_config.hooks.disable",
    ),
    re_path(
        make_app_pattern("/deploy_config/procfile/$", include_envs=False),
        views.ModuleDeployConfigViewSet.as_view({"post": "update_procfile"}),
        name="api.modules.deploy_config.procfile.update",
    ),
]


# Multi-editions specific start

try:
    from .urls_ext import urlpatterns as urlpatterns_ext

    urlpatterns += urlpatterns_ext
except ImportError:
    pass

# Multi-editions specific end
