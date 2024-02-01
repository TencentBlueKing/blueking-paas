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
    # 创建自定义上报
    databus_custom_create = bind_property(
        Operation,
        name="databus_custom_create",
        method="POST",
        path="/databus_custom_create/",
    )

    # 更新自定义上报
    databus_custom_update = bind_property(
        Operation,
        name="databus_custom_update",
        method="POST",
        path="/{collector_config_id}/databus_custom_update/",
    )

    # 采集项列表
    databus_list_collectors = bind_property(
        Operation, name="databus_list_collectors", method="GET", path="/databus_list_collectors/"
    )

    # ES-DSL查询接口
    esquery_dsl = bind_property(Operation, name="esquery_dsl", method="POST", path="/esquery_dsl/")
    # ES-SCROLL 查询接口
    esquery_scroll = bind_property(Operation, name="esquery_scroll", method="POST", path="/esquery_scroll/")
    # ES_MAPPING 查询接口
    esquery_mapping = bind_property(Operation, name="esquery_mapping", method="POST", path="/esquery_mapping/")


class Client(APIGatewayClient):
    """bk-log日志平台 API"""

    _api_name = "log-search"

    api = bind_property(Group, name="api")
