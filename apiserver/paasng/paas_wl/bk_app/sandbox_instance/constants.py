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

from blue_krill.data_types.enum import StrStructuredEnum

# SandboxInstance CR 的 API Group / Version, 由集群侧 sandbox-controller 负责协调
SANDBOX_INSTANCE_API_VERSION = "advanced.bkbcs.tencent.com/v1beta1"
SANDBOX_INSTANCE_KIND = "SandboxInstance"

# 运行时类, 沙箱 Pod 由 cube runtime 承载(一个 SandboxInstance 一个 MicroVM)
DEFAULT_RUNTIME_CLASS_NAME = "cube"

# 本期网络模式固定为 direct-cni
DEFAULT_NETWORK_MODE = "direct-cni"

# 触发重调度重启的注解 key(值为 RFC3339 时间戳, 值变化即触发一次)
RESTARTED_AT_ANNOTATION = "advanced.bkbcs.tencent.com/restartedAt"

# rootfs 系统盘相关默认值
ROOTFS_DISK_NAME = "rootfs"
ROOTFS_DISK_ROLE = "rootfsDisk"
ROOTFS_DISK_IMAGE = "rootdisk.img"
ROOTFS_DISK_SOURCE_PATH = "rootfs"
ROOTFS_DISK_FS_TYPE = "ext4"

# rootfs 持久化时, operator 自动创建的 PVC 后缀 / 存储卷名
STATE_VOLUME_NAME = "cube-state"


class DesiredState(StrStructuredEnum):
    """SandboxInstance 期望运行态, 通过 spec.desiredState 声明"""

    RUNNING = "Running"
    STOPPED = "Stopped"


class SandboxInstancePhase(StrStructuredEnum):
    """SandboxInstance 生命周期阶段, 见 status.phase"""

    PENDING = "Pending"
    CREATING = "Creating"
    RUNNING = "Running"
    STOPPING = "Stopping"
    STOPPED = "Stopped"
    FAILED = "Failed"
    TERMINATING = "Terminating"
