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

from paasng.utils.basic import make_app_pattern, re_path

from .views import DevSandboxEnvVarViewSet, DevSandboxViewSet

urlpatterns = [
    re_path(
        make_app_pattern(r"/dev_sandboxes/$", include_envs=False),
        DevSandboxViewSet.as_view({"get": "list", "post": "create"}),
        name="accessories.dev_sandbox.list_create",
    ),
    re_path(
        make_app_pattern(r"/dev_sandboxes/pre_deploy_check/$", include_envs=False),
        DevSandboxViewSet.as_view({"get": "pre_deploy_check"}),
        name="accessories.dev_sandbox.pre_deploy_check",
    ),
    re_path(
        make_app_pattern(r"/dev_sandboxes/(?P<dev_sandbox_code>[^/]+)/$", include_envs=False),
        DevSandboxViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="accessories.dev_sandbox.retrieve_destroy",
    ),
    re_path(
        make_app_pattern(r"/dev_sandboxes/(?P<dev_sandbox_code>[^/]+)/commit/$", include_envs=False),
        DevSandboxViewSet.as_view({"post": "commit"}),
        name="accessories.dev_sandbox.commit",
    ),
    re_path(
        make_app_pattern(r"/dev_sandboxes/(?P<dev_sandbox_code>[^/]+)/addons_services/$", include_envs=False),
        DevSandboxViewSet.as_view({"get": "list_addons_services"}),
        name="accessories.dev_sandbox.list_addons_services",
    ),
    re_path(
        make_app_pattern(r"/dev_sandboxes/(?P<dev_sandbox_code>[^/]+)/env_vars/$", include_envs=False),
        DevSandboxEnvVarViewSet.as_view({"get": "list", "post": "upsert"}),
        name="accessories.dev_sandbox.env_var.list_upsert",
    ),
    re_path(
        make_app_pattern(r"/dev_sandboxes/(?P<dev_sandbox_code>[^/]+)/env_vars/(?P<key>[^/]+)/$", include_envs=False),
        DevSandboxEnvVarViewSet.as_view({"delete": "destroy"}),
        name="accessories.dev_sandbox.env_var.destroy",
    ),
]
