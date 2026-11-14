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

# 创建时未指定 timeout 的默认存活时长。网关对缺省 timeout 的处理是永不过期
# （endAt 返回 2099 年），绕过 SDK 直接打接口就会留不回收的沙箱，因此在代理层兜底。
# 取值与 e2b SDK 的默认沙箱超时（300 秒）对齐，两条路径行为一致
DEFAULT_SANDBOX_TIMEOUT_SECONDS = 300

# 网关响应中承载数据面地址的字段，apiserver 必须改写它：
# 网关填的是集群内 Service 域名，集群外的 SDK 解析不到
DATA_PLANE_DOMAIN_FIELD = "domain"

# 网关响应中的沙箱标识字段
SANDBOX_ID_FIELD = "sandboxID"

# 创建请求与网关响应中的模板标识字段
TEMPLATE_ID_FIELD = "templateID"

# 创建请求中模板标识的旧字段名，底层 E2B 网关在 templateID 为空时回退到它
TEMPLATE_NAME_FIELD = "template"

# 网关响应中的运行状态字段，对账时以它为权威值
SANDBOX_STATE_FIELD = "state"

# 归档时的单批删除条数。终止记录没有关联对象，删除很轻，
# 分批只是为了不在一条语句里锁住过多行
ARCHIVE_BATCH_SIZE = 500

# 模板标识（SDK 创建沙箱时传入的 templateID）的格式。首尾必须是字母数字：
# 它要拼进 k8s 资源名，底层 E2B 网关还会把资源名写进标签值，两者都不接受首尾为连接符
TEMPLATE_ID_PATTERN = r"^[a-z][a-z0-9-]{0,29}[a-z0-9]$"

# 自定义模板在集群内的资源名为 ``{应用}--{模板标识}``。应用 code 与内置模板名都不能含 ``--``，
# 因此按它切分既能还原出模板标识，也不会与内置模板撞名
CUSTOM_RESOURCE_NAME_SEPARATOR = "--"

# 底层 E2B 网关把资源名写进 SandboxInstance 的标签值，标签值最长 63 个字符
RESOURCE_NAME_MAX_LENGTH = 63

# TODO 后续看资源情况确定是否补充 APP 维度的资源使用限制
# 模板规格的默认值与上下限
DEFAULT_TEMPLATE_CPU_COUNT = 2
DEFAULT_TEMPLATE_MEMORY_MB = 4096
MAX_TEMPLATE_CPU_COUNT = 4
MAX_TEMPLATE_MEMORY_MB = 4096
MIN_TEMPLATE_DISK_SIZE_MB = 1024
MAX_TEMPLATE_DISK_SIZE_MB = 102400

# 系统盘是放在 PVC 里的磁盘镜像文件，PVC 要比盘本身大，取值参照底层 E2B 网关的示例（20Gi 盘配 30Gi PVC）
TEMPLATE_PVC_SIZE_RATIO = 1.5

# 平台下发的 CR 都打上这个标签，同步只清理带标签的 CR，不碰集群里手工创建的
TEMPLATE_MANAGED_BY_LABEL = "paas.bk.tencent.com/managed-by"
TEMPLATE_MANAGED_BY_VALUE = "bkpaas-e2b-template"

# 底层 E2B 网关按这个标签回填沙箱的 templateID，值为资源名
GATEWAY_TEMPLATE_LABEL = "advanced.bkbcs.tencent.com/e2b-template"


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


class E2BGatewayOutcome(StrStructuredEnum):
    """网关调用指标 ``e2b_gateway_requests_total`` 的 outcome 取值"""

    SUCCESS = EnumField("success", label="调用成功")
    NOT_FOUND = EnumField("not_found", label="网关返回 404")
    TIMEOUT = EnumField("timeout", label="调用超时")
    UNAVAILABLE = EnumField("unavailable", label="网关不可达")
    ERROR = EnumField("error", label="网关返回错误")
