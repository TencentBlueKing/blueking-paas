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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum

# e2b SDK 在发请求前会本地校验 key 形如 ``e2b_`` + 十六进制串，不合格的 key 请求根本发不出去。
# 因此这两个常量不是风格选择，改动会直接导致标准 SDK 不可用。
API_KEY_PREFIX = "e2b_"
API_KEY_RANDOM_BYTES = 20

# 列表展示用的前缀长度，含 ``e2b_``。取 4 + 8，泄露的熵不足以爆破
API_KEY_DISPLAY_PREFIX_LEN = len(API_KEY_PREFIX) + 8

# 认证头名称由 e2b 协议固定
API_KEY_HEADER = "X-API-Key"

# 单个应用同时有效的 key 数量上限，留出轮换窗口即可，不需要很大
MAX_ACTIVE_KEYS_PER_APP = 5

# 生成 key 时的哈希碰撞重试次数。160 位随机下碰撞概率可忽略，这里只是兜底
KEY_GENERATE_MAX_RETRIES = 3

# 创建沙箱的等待上限。池子未命中时网关要现场拉起实例，比其余控制面调用慢得多。
# 取 30 秒是需求给的创建耗时上限，超过即向 SDK 返回 408 建议重试
GATEWAY_CREATE_TIMEOUT_SECONDS = 30

# 其余控制面调用都是查询或状态变更，网关侧没有耗时操作
GATEWAY_REQUEST_TIMEOUT_SECONDS = 10

# 网关响应中承载数据面地址的字段，apiserver 必须改写它：
# 网关填的是集群内 Service 域名，集群外的 SDK 解析不到
DATA_PLANE_DOMAIN_FIELD = "domain"

# 网关响应中的沙箱标识字段
SANDBOX_ID_FIELD = "sandboxID"

# 网关响应中的运行状态字段，对账时以它为权威值
SANDBOX_STATE_FIELD = "state"

# 归档时的单批删除条数。终止记录没有关联对象，删除很轻，
# 分批只是为了不在一条语句里锁住过多行
ARCHIVE_BATCH_SIZE = 500


class E2BSandboxStatus(StrStructuredEnum):
    """E2B 标准沙箱状态"""

    RUNNING = EnumField("running", label="运行中")
    PAUSED = EnumField("paused", label="已暂停")
    # 被销毁、被 gateway 超时回收，或对账时发现网关侧已不存在
    TERMINATED = EnumField("terminated", label="已终止")

    @classmethod
    def active_values(cls) -> list[str]:
        """仍占用底层资源、需要参与对账的状态。"""
        return [cls.RUNNING.value, cls.PAUSED.value]


class E2BReconcileOutcome(StrStructuredEnum):
    """对账指标 ``e2b_sandbox_reconciled`` 的 outcome 取值"""

    CONVERGED = EnumField("converged", label="本地状态已收敛")
    # 网关返回了本枚举之外的状态，说明平台的状态定义落后于网关版本。
    UNKNOWN_STATE = EnumField("unknown_state", label="网关状态无法识别")
    ORPHAN_KILLED = EnumField("orphan_killed", label="已销毁孤儿实例")
    ORPHAN_KILL_FAILED = EnumField("orphan_kill_failed", label="销毁孤儿失败")
    CLUSTER_SKIPPED = EnumField("cluster_skipped", label="集群被跳过")
