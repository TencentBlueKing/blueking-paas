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

from dataclasses import asdict, dataclass, fields


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
        return [getattr(self, field.name) for field in fields(self)]

    @classmethod
    def as_label_keys(cls) -> list[str]:
        return [field.name for field in fields(cls)]


@dataclass
class RedisInstanceStatus:
    """单个实例的采集结果

    取值一律遵循 "显式缺失" 约定:
    - None: 取不到 (没有 exporter / k8s 查询失败 / 样本不存在), 对应指标不产出样本
    - bool: 已确认的结论, False 为否定 (代表 Pod 未就绪 / 确认没有 Pod / exporter 取数失败)

    k8s_state_missing / usage_fetch_skipped 是采集器侧的降级标记, 供 collect_success 判断使用.
    """

    instance: RedisInstance
    alive: bool | None = None
    oom_killed: bool | None = None
    # 有 exporter 且取数成功为 True, 取数失败为 False; None 表示实例没有 exporter
    exporter_up: bool | None = None
    memory_usage_rate: float | None = None
    connection_usage_rate: float | None = None
    # 所有 DB 的 key 总数 (redis_db_keys 按 db 标签求和)
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
