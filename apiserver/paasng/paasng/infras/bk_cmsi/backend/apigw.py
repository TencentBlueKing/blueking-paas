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
    # 发送邮件
    send_mail = bind_property(
        Operation,
        name="v1_send_mail",
        method="POST",
        path="/v1/send_mail/",
    )
    # 发送短信
    send_sms = bind_property(
        Operation,
        name="v1_send_sms",
        method="POST",
        path="/v1/send_sms/",
    )
    # 发送微信
    send_weixin = bind_property(
        Operation,
        name="v1_send_weixin",
        method="POST",
        path="/v1/send_weixin/",
    )


class Client(APIGatewayClient):
    """蓝鲸消息通知 API"""

    _api_name = "bk-cmsi"

    api = bind_property(Group, name="api")
