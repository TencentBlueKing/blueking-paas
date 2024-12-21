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

from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property


class Group(OperationGroup):
    # 创建 websocket session
    create_web_console_sessions = bind_property(
        Operation,
        name="create_web_console_sessions",
        method="POST",
        path="/{version}/webconsole/api/portal/projects/{project_id_or_code}/"
        "clusters/{cluster_id}/web_console/sessions/",
    )


class Client(APIGatewayClient):
    """bcs-services 提供的网关 client"""

    _api_name = "bcs-api-gateway"
    api = bind_property(Group, name="api")
