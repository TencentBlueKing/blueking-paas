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
