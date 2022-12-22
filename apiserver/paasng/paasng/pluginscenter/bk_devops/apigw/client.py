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
from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property


class Group(OperationGroup):
    # 获取看板 summary 数据
    v4_app_metrics_summary = bind_property(
        Operation,
        name="v4_app_metrics_summary",
        method="GET",
        path="/v4/apigw-app/metrics/projectId/{projectId}/summary",
    )


class Client(APIGatewayClient):
    """devops
    蓝盾devops平台OpenApi
    """

    _api_name = "devops"

    api = bind_property(Group, name="api")
