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
        make_app_pattern(r'/manifest_ext/$', include_envs=True),
        views.CNativeAppManifestExtViewset.as_view({'get': 'retrieve'}),
        name='api.cnative.retrieve_manifest_ext',
    ),
    re_path(
        make_app_pattern(r'/bkapp_model/manifests/current/$', include_envs=False),
        views.BkAppModelManifestsViewset.as_view({'get': 'retrieve', 'put': 'replace'}),
        name='api.bkapp_model.current_manifests',
    ),
    # 进程配置
    re_path(
        make_app_pattern(r'/bkapp_model/process_specs/$', include_envs=False),
        views.ModuleProcessSpecViewSet.as_view({"get": "retrieve", "post": "batch_upsert"}),
        name='api.bkapp_model.process_specs',
    ),
    # 钩子命令
    re_path(
        make_app_pattern(r'/bkapp_model/deploy_hooks/$', include_envs=False),
        views.ModuleDeployHookViewSet.as_view({"post": "upsert"}),
        name='api.bkapp_model.deploy_hooks',
    ),
    re_path(
        make_app_pattern(r'/bkapp_model/deploy_hooks/(?P<hook_type>[^/]+)/$', include_envs=False),
        views.ModuleDeployHookViewSet.as_view({"get": "retrieve"}),
        name='api.bkapp_model.deploy_hooks.detail',
    ),
]
