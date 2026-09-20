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

"""Redis 实例指标采集的数据结构"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RedisInstance:
    """一个已分配实例的身份信息"""

    bk_instance: str
    bk_cluster: str
    namespace: str
    bk_app_code: str
    bk_module: str
    bk_env: str

    def as_label_values(self) -> list[str]:
        return [self.bk_instance, self.bk_cluster, self.namespace, self.bk_app_code, self.bk_module, self.bk_env]

    @classmethod
    def as_label_keys(cls) -> list[str]:
        return ["bk_instance", "bk_cluster", "namespace", "bk_app_code", "bk_module", "bk_env"]


@dataclass
class RedisInstanceStatus:
    """单个实例的采集结果, 值为 None 表示采集失败(该指标不产出样本)"""

    instance: RedisInstance
    alive: bool | None = None
    memory_usage_rate: float | None = None
    connection_usage_rate: float | None = None
    oom_killed: bool | None = None
    # 有 exporter 且取数成功为 True, 取数失败为 False; None 表示实例没有 exporter
    exporter_up: bool | None = None
    # 所有 DB 的 key 总数 (redis_db_keys 按 db 标签求和); None 表示取不到该样本
    db_keys: float | None = None
    # True 表示实例的 k8s 状态读不到 (集群或命名空间查询失败)
    k8s_state_missing: bool = False
    # True 表示实例有 exporter 但因 deadline 截断/任务异常未被回填 (区别于 exporter 真的取数失败)
    usage_fetch_skipped: bool = False

    def as_dict(self) -> dict:
        """转换为可序列化的普通字典 (嵌套的 instance 一并转换)"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RedisInstanceStatus":
        """由 as_dict() 的结果还原"""
        return cls(instance=RedisInstance(**data["instance"]), **{k: v for k, v in data.items() if k != "instance"})
