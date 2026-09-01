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


class E2BError(Exception):
    """e2b 兼容层的异常基类"""


class E2BApiKeyQuotaExceeded(E2BError):
    """有效 key 数量已达上限"""


class E2BApiKeyGenerateError(E2BError):
    """生成唯一 key 失败"""


class E2BSandboxNotFound(E2BError):
    """沙箱不存在，或存在但不属于发起方"""


class E2BClusterUnavailable(E2BError):
    """没有可用于 e2b 沙箱的集群"""


class E2BClusterNotConfigured(E2BError):
    """指定集群没有登记 e2b 配置，或配置已被停用"""


class E2BGatewayError(E2BError):
    """调用底层网关失败的基类"""


class E2BGatewayUnavailable(E2BGatewayError):
    """网关连不上：DNS、连接被拒、入口故障等"""


class E2BGatewayTimeout(E2BGatewayError):
    """网关在超时窗口内没有返回"""


class E2BGatewayNotFound(E2BGatewayError):
    """网关侧不存在该沙箱

    与 E2BSandboxNotFound 分开：那个是本地归属表判定的结果，这个是网关的回答。
    本地有记录而网关说没有，说明沙箱已被回收，两者对外都是 404 但成因不同。
    """
