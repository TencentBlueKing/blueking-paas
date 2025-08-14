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

"""这里放由于接口已注册到 APIGW, 不能即时下线的接口"""

from typing import List, Union

from rest_framework.response import Response

from paasng.accessories.log.serializers import LogQueryParamsSLZ
from paasng.accessories.log.views.logs import ModuleStdoutLogAPIView, ModuleStructuredLogAPIView
from paasng.infras.accounts.permissions.application import BaseAppPermission
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.platform.applications.models import Application
from paasng.platform.modules.models import Module
from paasng.utils.datetime import convert_timestamp_to_str


class AllowAnyActionsOnAllApps(BaseAppPermission):
    """This class pass all permission checks.

    Why we need this class:

    - Legacy system log API reuse the user log API View which use ApplicationCodeInPathMixin
      to get the application and module instances.
    - ApplicationCodeInPathMixin requires at least one application permission class
      or it won't work.
    - The system log API doesn't need any permission check
    """

    def has_object_permission(self, request, view, obj: Union[Application, Module]):
        return True


class V1StdoutLogAPIView(ModuleStdoutLogAPIView):
    # 该接口已注册到 APIGW
    # 网关名称 search_standard_log_with_post
    # 请勿随意修改该接口协议
    def query_logs_scroll(self, request, code, module_name, environment=None):
        response = super().query_logs_scroll(request, code, module_name, environment)
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

    # 该接口已注册到 APIGW
    # 网关名称 search_standard_log_with_get
    # 请勿随意修改该接口协议
    def query_logs_scroll_with_get(self, request, code, module_name, environment=None):
        return self.query_logs_scroll(request, code, module_name, environment=None)


class V1SysStructuredLogAPIView(ModuleStructuredLogAPIView):
    permission_classes: List = [AllowAnyActionsOnAllApps, sysapi_client_perm_class(ClientAction.READ_APPLICATIONS)]

    # 该接口已注册到 APIGW
    # 网关名称 search_structured_log
    # 请勿随意修改该接口协议
    def query_logs(self, request, code, module_name, environment=None):
        slz = LogQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data
        offset = query_params["offset"]
        limit = query_params["limit"]
        response = super().query_logs(request, code, module_name, environment)
        data = response.data
        return Response(
            {
                "code": 0,
                "data": {
                    "logs": [
                        # 与重构前的 LogLine 字段一致
                        {
                            "app_code": log["app_code"],
                            "environment": log["environment"],
                            "process_id": log["process_id"],
                            "stream": log["stream"],
                            "message": log["message"],
                            "detail": log["detail"],
                            "ts": convert_timestamp_to_str(log["timestamp"]),
                        }
                        for log in data["logs"]
                    ],
                    "page": {
                        # page 的类型为 int，这里要用整除
                        "page": query_params.get("page") or (offset // limit + 1),
                        "page_size": limit,
                        "total": data["total"],
                    },
                    "dsl": data["dsl"],
                },
            }
        )

    def query_logs_get(self, request, code, module_name, environment=None):
        return self.query_logs(request, code, module_name, environment)
