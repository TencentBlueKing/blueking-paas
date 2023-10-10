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
    # 开发者中心创建lesscode类型应用时同步创建lesscode应用
    create_project_by_app = bind_property(
        Operation,
        name="create_project_by_app",
        method="POST",
        path="/create_project_by_app",
    )

    # 根据 appCode 和 moduleCode 获取项目id和名称
    find_project_by_app = bind_property(
        Operation,
        name="find_project_by_app",
        method="GET",
        path="/find-project-by-app",
    )

    # 根据项目id和版本号获取项目源码包
    project_release_package = bind_property(
        Operation,
        name="project_release_package",
        method="GET",
        path="/project/release/package",
    )

    # 获取用户有权限的项目列表及项目版本号列表
    project_releases = bind_property(
        Operation,
        name="project_releases",
        method="GET",
        path="/project/releases",
    )


class Client(APIGatewayClient):
    """bk-lesscode
    蓝鲸可视化平台提供的openapi
    """

    _api_name = "bk-lesscode"

    api = bind_property(Group, name="api")
