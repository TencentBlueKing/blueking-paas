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

# 异常信息只能包含错误类别与服务端返回的业务错误描述，不得包含明文、信封、私钥或请求头


class KMSError(Exception):
    """KMS 凭证托管相关异常的基类"""


class KMSConfigError(KMSError):
    """KMS 配置缺失或不完整"""


class KMSValidationError(KMSError, ValueError):
    """参数不符合 KMS 约束（长度、授权范围等），未发起远程请求"""


class KMSCryptoError(KMSError):
    """服务端下发的加密信息不受支持，或公钥不可用，无法完成混合加密"""


class KMSRequestError(KMSError):
    """与 KMS 管理接口的通信失败：网络错误、超时、HTTP 状态异常或响应结构不符合预期"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class KMSAPIError(KMSError):
    """KMS 返回业务错误（响应 code 不为 0）"""

    def __init__(self, code: int, message: str):
        super().__init__(f"KMS api error, code: {code}, message: {message}")
        self.code = code
        self.message = message


class KMSCredentialMismatchError(KMSError):
    """同名凭证已存在，但 scope、授权范围或加密设置与本配置版本的期望不一致。不复用，也不覆盖"""


class KMSSecretNotReadyError(KMSError):
    """目标 Secret 在超时时间内未就绪。reason 为安全的分类，不包含 Secret 内容或 ESO 的 message"""

    def __init__(self, reason: str):
        super().__init__(f"KMS secret is not ready, reason: {reason}")
        self.reason = reason
