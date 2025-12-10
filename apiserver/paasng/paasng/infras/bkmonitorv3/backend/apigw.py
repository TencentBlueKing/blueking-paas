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
    # 创建 APM 应用
    create_apm_application = bind_property(
        Operation,
        name="create_apm_application",
        method="POST",
        path="/app/apm/create_apm_application/",
    )

    # 快速创建 APM 应用
    apm_create_application = bind_property(
        Operation,
        name="apm_create_application",
        method="POST",
        path="/app/apm/create_application/",
    )

    # 创建空间
    metadata_create_space = bind_property(
        Operation,
        name="metadata_create_space",
        method="POST",
        path="/app/metadata/create_space/",
    )

    # 更新空间
    metadata_update_space = bind_property(
        Operation,
        name="metadata_update_space",
        method="POST",
        path="/app/metadata/update_space/",
    )

    # 查询空间实例详情
    metadata_get_space_detail = bind_property(
        Operation,
        name="metadata_get_space_detail",
        method="GET",
        path="/app/metadata/get_space_detail/",
    )

    # 查询告警记录
    search_alert = bind_property(
        Operation,
        name="search_alert",
        method="POST",
        path="/app/alert/search/",
    )

    # 查询告警策略 (迁移)
    search_alarm_strategy_v3 = bind_property(
        Operation,
        name="search_alarm_strategy_v3",
        method="POST",
        path="/app/alarm_strategy/search/v3/",
    )

    # 统一查询时序数据
    promql_query = bind_property(
        Operation,
        name="promql_query",
        method="POST",
        path="/app/data_query/graph_promql_query/",
    )

    # 导入 AsCode 配置
    as_code_import_config = bind_property(
        Operation,
        name="as_code_import_config",
        method="POST",
        path="/app/as_code/import_config/",
    )

    # 快捷应用内置仪表盘
    quick_import_dashboard = bind_property(
        Operation,
        name="quick_import_dashboard",
        method="POST",
        path="/app/dashboard/quick_import_dashboard/",
    )


class Client(APIGatewayClient):
    """bk-monitor API 网关客户端"""

    _api_name = "bk-monitor"

    api = bind_property(Group, name="api")
