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
from functools import partial

from paasng.utils.basic import make_app_pattern, re_path

from . import views

# In legacy architecture, all workloads's APIs starts with a fixed prefix "/svc_workloads" and use
# a slightly different format. While the prefix is not required in the new architecture, we have
# to keep it to maintain backward-compatibility.
#
# This function helps up to build paths with the legacy prefix.
#
# TODO: Remove the 'svc_workloads' prefix and clean up the URL paths.
make_app_pattern_legacy_wl = partial(make_app_pattern, prefix="svc_workloads/api/scheduling/applications/")


urlpatterns = [
    re_path(
        make_app_pattern_legacy_wl(r"/egress_gateway_infos/$"),
        views.EgressGatewayInfosViewSet.as_view({"post": "create"}),
        name="api.egress_gateway_infos",
    ),
    re_path(
        make_app_pattern_legacy_wl(r"/egress_gateway_infos/default/$"),
        views.EgressGatewayInfosViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="api.egress_gateway_infos.default",
    ),
]
