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

from bkapi_client_core.esb import ESBClient, Operation, OperationGroup, bind_property
from bkapi_client_core.esb import generic_type_partial as _partial
from bkapi_client_core.esb.django_helper import get_client_by_username as _get_client_by_username


class Group(OperationGroup):
    """ESB 上注册的蓝鲸消息通知 API"""

    # 发送邮件
    send_mail = bind_property(
        Operation,
        name="send_mail",
        method="POST",
        path="/api/c/compapi/v2/cmsi/send_mail/",
    )
    # 发送短信
    send_sms = bind_property(
        Operation,
        name="send_sms",
        method="POST",
        path="/api/c/compapi/v2/cmsi/send_sms/",
    )
    # 发送微信
    send_weixin = bind_property(
        Operation,
        name="send_weixin",
        method="POST",
        path="/api/c/compapi/v2/cmsi/send_weixin/",
    )
    # 发送企业微信(仅 esb 有该通知渠道)
    send_rtx = bind_property(
        Operation,
        name="send_rtx",
        method="POST",
        path="/api/c/compapi/v2/cmsi/send_rtx/",
    )


class Client(ESBClient):
    """ESB Components"""

    api = bind_property(Group, name="api")


get_client_by_username = _partial(Client, _get_client_by_username)
