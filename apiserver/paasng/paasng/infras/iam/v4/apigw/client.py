# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from bkapi_client_core.apigateway import APIGatewayClient, OperationGroup, bind_property


class Group(OperationGroup):
    """网关 bkiam 的 Operation 定义

    V4 的接口按用途分为鉴权、模型注册、管理空间与用户组、授权、跨系统共享、申请链接六类。
    各类接口由对应的子需求在此按类追加 `bind_property(Operation, ...)` 定义，
    调用时统一经 `paasng.infras.iam.v4.http.BKIAMV4BaseClient` 发起，
    以复用其 header 注入、翻页、分批与错误处理逻辑。
    """


class Client(APIGatewayClient):
    """蓝鲸权限中心 V4 提供的 OpenAPI

    note: V4 的网关名为 `bkiam`，与 V3 的 `bk-iam` 是两个独立网关，授权数据互不相通
    """

    _api_name = "bkiam"

    api = bind_property(Group, name="api")
