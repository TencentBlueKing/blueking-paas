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
    # bkapi resource app_codecc_customPipeline_new
    # 新版通用触发个性化流水线接口
    app_codecc_custom_pipeline_new = bind_property(
        Operation,
        name="app_codecc_custom_pipeline_new",
        method="POST",
        path="/v2/apigw-app/codecc/task/pipelines/custom/trigger/new",
    )

    # bkapi resource app_codecc_buildId_mapping
    # 根据codeccBuildId查询buildId映射
    app_codecc_build_id_mapping = bind_property(
        Operation,
        name="app_codecc_build_id_mapping",
        method="POST",
        path="/v2/apigw-app/codecc/task/buildId",
    )

    # bkapi resource app_codecc_build_task_info
    # 根据codeccBuildId查询buildId映射
    app_codecc_build_task_info = bind_property(
        Operation,
        name="app_codecc_build_task_info",
        method="POST",
        path="/v2/apigw-app/codecc/task/getTaskBuildInfo",
    )

    # bkapi resource app_codecc_defect_statistic
    # 获取codecc告警统计原始数据
    app_codecc_defect_statistic = bind_property(
        Operation,
        name="app_codecc_defect_statistic",
        method="POST",
        path="/v2/apigw-app/codecc/defect/statistic",
    )

    # bkapi resource app_codecc_defect_statistic_dimension
    # 获取codecc告警统计维度数据
    app_codecc_defect_statistic_dimension = bind_property(
        Operation,
        name="app_codecc_defect_statistic_dimension",
        method="POST",
        path="/v2/apigw-app/codecc/defect/statistic/dimension",
    )

    # bkapi resource app_codecc_defect_statistic_summary
    # 获取codecc告警统计维度数据
    app_codecc_defect_statistic_summary = bind_property(
        Operation,
        name="app_codecc_defect_statistic_summary",
        method="POST",
        path="/v2/apigw-app/codecc/defect/statistic/summary",
    )

    # bkapi resource app_codecc_task_metrics
    # 查询codecc任务度量信息
    app_codecc_task_metrics = bind_property(
        Operation,
        name="app_codecc_task_metrics",
        method="GET",
        path="/v2/apigw-app/codecc/defect/metric/{taskId}",
    )

    # 根据任务id查询所有工具问题数
    app_codecc_tool_defect_count = bind_property(
        Operation,
        name="app_codecc_tool_defect_count",
        method="GET",
        path="/v2/apigw-app/codecc/defect/tool/defect/count/list",
    )


class Client(APIGatewayClient):
    """Bkapi devops client"""

    _api_name = "devops"

    api = bind_property(Group, name="api")
