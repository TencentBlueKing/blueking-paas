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
    # 创建APM应用
    create_apm_application = bind_property(
        Operation,
        name="create_apm_application",
        method="POST",
        path="/create_apm_application/",
    )

    # 快速创建APM应用
    apm_create_application = bind_property(
        Operation,
        name="apm_create_application",
        method="POST",
        path="/apm/create_application/",
    )

    # 创建空间
    metadata_create_space = bind_property(
        Operation,
        name="metadata_create_space",
        method="POST",
        path="/metadata_create_space/",
    )

    # 更新空间
    metadata_update_space = bind_property(
        Operation,
        name="metadata_update_space",
        method="POST",
        path="/metadata_update_space/",
    )

    # 查询空间实例详情
    metadata_get_space_detail = bind_property(
        Operation,
        name="metadata_get_space_detail",
        method="GET",
        path="/metadata_get_space_detail/",
    )

    # 查询告警
    search_alert = bind_property(
        Operation,
        name="search_alert",
        method="POST",
        path="/search_alert/",
    )


class Client(APIGatewayClient):
    """bkmonitorv3
    监控平台v3上云版本
    """

    _api_name = "bkmonitorv3"

    api = bind_property(Group, name="api")
