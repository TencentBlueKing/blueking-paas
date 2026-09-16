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
import logging
import re
from contextlib import contextmanager
from typing import Iterator

from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


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

    def __init__(self, message: str, code: int | None = None, request_id: str | None = None):
        super().__init__(self.parse_quota_message(message))
        self.code = code
        # 权限中心侧的请求 ID，用于跨系统排查。仅在字符串化时附加，
        # 以保证 message 仍是可直接展示给用户的内容
        self.request_id = request_id

    def __str__(self) -> str:
        if self.request_id:
            return f"{self.message} (iam request_id: {self.request_id})"
        return str(self.message)

    def parse_quota_message(self, message: str) -> str:
        """权限中心给多个用户添加用户组权限时，会因为其中一个用户的额度超限导致添加失败，权限中心未针对用户超限定义单独的错误码，超限的用户也只能从错误信息中提取。

        :param message: 原始报错信息，如：请求第三方 API 错误: request iam error! Request=[http_post /api/v1/web/group-members request_id=2bba2ee9651c4d28b2bc8f3075d68f93] Response[code=1901409, message=conflict:[Handler:checkSubjectGroupsQuota] subject {0 user BruceLee 4102444800 0001-01-01 00:00:00 +0000 UTC} can only have 100 groups in system bk_plugins.[current 100] => [Raw:Error] quota error] (REMOTE_REQUEST_ERROR)
        :return: 用户 BruceLee 在蓝鲸权限中心的角色数已经超出了 100 个的限制
        """
        # 定义正则表达式模式，匹配用户信息和超限原因
        user_pattern = r"user (\w+)"
        quota_pattern = r"can only have (\d+) groups"

        # 使用正则表达式查找匹配的用户信息
        user_match = re.search(user_pattern, message)
        quota_match = re.search(quota_pattern, message)

        if user_match and quota_match:
            user = user_match.group(1)
            quota = quota_match.group(1)
            return _(f"用户 {user} 在蓝鲸权限中心的角色数已经超出了 {quota} 个的限制")  # noqa: INT001
        else:
            # 没匹配到则返回原始的错误信息
            return message


class BKIAMApiHTTPError(BKIAMApiError):
    """权限中心返回了非 2xx 的 HTTP 状态码

    V4 以 HTTP 状态码表达错误语义（如 409 表示资源已存在），调用方需要据此走幂等分支时，
    可通过 `status_code` 判断，而不必解析错误信息。
    """

    def __init__(self, message: str, status_code: int | None, request_id: str | None = None):
        super().__init__(message, request_id=request_id)
        self.status_code = status_code


class InvalidIAMIdentifierError(ValueError):
    """本地模型标识符不满足权限中心 V4 的命名约束

    同步命令在提交到 V4 之前校验，命中时立即失败并列出全部违规标识符。
    """

    def __init__(self, identifiers: list[str]):
        self.identifiers = identifiers
        super().__init__(f"以下标识符不满足 IAM V4 命名约束: {', '.join(identifiers)}")


class BKIAMAuthCheckError(BKIAMGatewayServiceError):
    """鉴权判定调用失败

    V3 经 SDK 鉴权、V4 经 HTTP 鉴权，两者原始的异常类型不同。V3 实现将 SDK 的 AuthAPIError
    包装为本异常，V4 实现抛出的 BKIAMApiError 系列同属 BKIAMGatewayServiceError，
    调用方据此捕获基类即可，无需感知版本差异，也不必再 import SDK 的异常。

    note: 判定失败不等于无权限。捕获方须按未授权处理，不得因调用失败而放行
    """


class BKIAMCapabilityNotSupportedError(BKIAMGatewayServiceError):
    """目标权限中心版本尚未提供所需的能力

    用于 V4 尚未补齐的管理接口：抽象接口保留方法定义，V4 实现抛出该异常而非静默返回成功。
    业务主流程应捕获后记录日志并继续，避免把成员变更、应用删除等打断。
    """

    def __init__(self, capability: str, detail: str = ""):
        message = _("权限中心 V4 暂未提供该能力：{capability}").format(capability=capability)
        if detail:
            message = f"{message}（{detail}）"
        super().__init__(message)
        self.capability = capability


@contextmanager
def ignore_unsupported_capability() -> Iterator[None]:
    """捕获 V4 暂缺能力并记日志，让上层主流程继续"""
    try:
        yield
    except BKIAMCapabilityNotSupportedError as exc:
        logger.warning("IAM 暂未提供该能力，已忽略：%s", exc)
