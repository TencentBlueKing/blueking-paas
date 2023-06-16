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
from django.http import Http404
from django.urls import include, re_path, resolve
from django.views.generic import View

urlpatterns = [
    # 为了方便统计已迁移的接口和保持接口地址不变, apiserver 重新实现的 workloads 下的 enduser view 注册到这里
    # TODO: 在 workloads 项目代码完全迁移后, 路由重新注册到各自的 urls.py
    re_path(r"^api/scheduling/", include("paas_wl.networking.egress.urls_enduser")),
    re_path("^api/services/", include("paas_wl.networking.ingress.urls_enduser")),
    re_path(r"^api/processes/", include("paas_wl.workloads.processes.urls_enduser")),
    re_path("^api/cnative/specs/", include("paas_wl.cnative.specs.urls_enduser")),
    re_path(r"^api/credentials/", include("paas_wl.workloads.images.urls_enduser")),
    re_path(r"", include("paas_wl.admin.urls")),
]


def resolve_workloads_path(path: str):
    return resolve("/" + path, urlconf=__name__)


class SvcWorkloadsEndUserView(View):
    def dispatch(self, request, *args, **kwargs):
        if "path" not in kwargs:
            raise Http404

        path = kwargs["path"]
        match = resolve_workloads_path(path)
        return match.func(request, *match.args, **match.kwargs)
