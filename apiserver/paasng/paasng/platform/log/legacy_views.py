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
"""这里放由于接口已注册到 APIGW, 不能即时下线的接口"""
from typing import List

from rest_framework.response import Response

from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_required
from paasng.platform.log.views import ModuleStdoutLogAPIView, ModuleStructuredLogAPIView
from paasng.utils.datetime import convert_timestamp_to_str


class LegacyStdoutLogAPIView(ModuleStdoutLogAPIView):
    # 网关名称 search_standard_log_with_post
    def query_logs_scroll(self, request, code, module_name, environment=None):
        response = super().query_logs_scroll(request, code, module_name, environment).data
        data = response.data
        return Response(
            {
                "code": 0,
                "data": {
                    "scroll_id": data["scroll_id"],
                    "logs": [
                        # 与重构前的 StandardOutputLogLine 字段一致
                        {
                            "environment": log["environment"],
                            "process_id": log["process_id"],
                            "pod_name": log["pod_name"],
                            "message": log["message"],
                            "timestamp": convert_timestamp_to_str(log["timestamp"]),
                        }
                        for log in data["logs"]
                    ],
                    "total": data["total"],
                    "dsl": data["dsl"],
                },
            }
        )

    # 网关名称 search_standard_log_with_get
    def query_logs_scroll_with_get(self, request, code, module_name, environment=None):
        return self.query_logs_scroll(request, code, module_name, environment=None)


class LegacySysStructuredLogAPIView(ModuleStructuredLogAPIView):
    permission_classes: List = []

    # 网关名称 search_structured_log
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def query_logs(self, request, code, module_name, environment=None):
        response = super().query_logs(request, code, module_name, environment)
        data = response.data
        return Response(
            {
                "code": 0,
                "data": {
                    "logs": [
                        # 与重构前的 LogLine 字段一致
                        {
                            "region": log["region"],
                            "app_code": log["app_code"],
                            "environment": log["environment"],
                            "process_id": log["process_id"],
                            "pod_name": log["pod_name"],
                            "stream": log["stream"],
                            "message": log["message"],
                            "detail": log["detail"],
                            "ts": convert_timestamp_to_str(log["timestamp"]),
                        }
                        for log in data["logs"]
                    ],
                    "page": {
                        "page": request.query_params.get("page"),
                        "page_size": request.query_params.get("page_size"),
                        "total": data["total"],
                    },
                    "dsl": data["dsl"],
                },
            }
        )
