# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import prometheus_client
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views import View
from prometheus_client.registry import CollectorRegistry


class AuthenticatedMetricsView(View):
    key_username = "client_id"
    key_password = "user_token"

    @property
    def registry(self):
        return prometheus_client.REGISTRY

    def get(self, request, *args, **kwargs):
        username = request.GET.get(self.key_username, '')
        password = request.GET.get(self.key_password, '')
        if not (username and password) or password != settings.METRIC_CLIENT_TOKEN_DICT.get(username):
            return HttpResponseForbidden(
                f"permission denied, no valid {self.key_username}/{self.key_password} provided",
            )

        registry = self.registry
        metrics_page = prometheus_client.generate_latest(registry)
        return HttpResponse(metrics_page, content_type=prometheus_client.CONTENT_TYPE_LATEST)


class CollectorMetricsView(AuthenticatedMetricsView):
    def get_collectors(self):
        raise NotImplementedError

    @property
    def registry(self):
        register = CollectorRegistry(auto_describe=True)

        for collector in self.get_collectors():
            register.register(collector)

        return register
