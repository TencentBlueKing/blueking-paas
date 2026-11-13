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


class E2BTemplateNotFound(E2BError):
    """创建所用的模板在网关侧不存在

    平台登记表里有、网关侧没有，说明两边配置漂移。与网关在查询/销毁时返回的
    「沙箱不存在」分开，否则用户看到的会是与操作无关的报错。
    """


class E2BTemplateAlreadyExists(E2BError):
    """模板标识已被占用：同一应用下重名，或与内置模板重名"""


class E2BTemplateQuotaExceeded(E2BError):
    """应用的自定义模板数量已达上限"""


class E2BTemplateIDTooLong(E2BError):
    """模板标识加上应用前缀后，资源名超出长度上限"""


class E2BTemplateInUse(E2BError):
    """模板下还有未终止的沙箱

    删除池子会连带销毁它名下的全部实例，包括用户正在用的沙箱，所以这种情况下拒绝删除。
    """


class E2BTemplateSyncInProgress(E2BError):
    """另一次模板下发还没结束

    全量同步与单模板同步都会覆盖、清理集群里的 CR，并发执行时旧状态会盖掉新状态，因此互斥(全局维度互斥)。
    """


class E2BClusterUnavailable(E2BError):
    """没有可用于 e2b 沙箱的集群"""


class E2BClusterNotConfigured(E2BError):
    """指定集群没有登记 e2b 配置"""


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
