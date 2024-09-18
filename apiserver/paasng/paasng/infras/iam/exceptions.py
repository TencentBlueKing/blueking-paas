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
import re
from typing import Optional

from django.utils.translation import gettext_lazy as _


class BKIAMGatewayServiceError(Exception):
    """This error indicates that there's something wrong when operating bk-iam's
    API Gateway resource. It's a wrapper class of API SDK's original exceptions
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BKIAMApiError(BKIAMGatewayServiceError):
    """When calling the bk-iam api, bk-iam returns an error message,
    which needs to be captured and displayed to the user on the page
    """

    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(self.parse_quota_message(message))
        self.code = code

    def parse_quota_message(self, message: str) -> str:
        """权限中心给多个用户添加用户组权限中，会因为其中一个用户的额度超限导致添加失败，希望能将错误信息语义化的展示出来。
        权限中心未针对用户超限定义单独的错误码，超限的用户也只能从错误信息中提取。

        :param message: 原始报错信息，如：请求第三方 API 错误: request iam error! Request=[http_post /api/v1/web/group-members request_id=2bba2ee9651c4d28b2bc8f3075d68f93] Response[code=1901409, message=conflict:[Handler:checkSubjectGroupsQuota] subject {0 user BruceLee 4102444800 0001-01-01 00:00:00 +0000 UTC} can only have 100 groups in system bk_plugins.[current 100] => [Raw:Error] quota error] (REMOTE_REQUEST_ERROR)
        :return: 用户 BruceLee 在蓝鲸权限中心的角色数已经超出了 100 个的限制
        """
        # 定义正则表达式模式，匹配用户信息和超限原因
        user_pattern = r"user (\w+)"
        quota_pattern = r"quota error"

        # 使用正则表达式查找匹配的用户信息
        user_match = re.search(user_pattern, message)
        quota_match = re.search(quota_pattern, message)

        if user_match and quota_match:
            user = user_match.group(1)
            return _(f"用户 {user} 在蓝鲸权限中心的角色数已经超出了 100 个的限制")
        else:
            # 没匹配到则返回原始的错误信息
            return message
