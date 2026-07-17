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
from decimal import Decimal

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class SandboxStatus(StrStructuredEnum):
    """Different status of sandbox."""

    PENDING = EnumField("pending", label="waiting to be run")
    RUNNING = EnumField("running", label="ready to execute commands")
    STOPPED = EnumField("stopped", label="stopped and can become running")
    DELETED = EnumField("deleted", label="deleted and no longer available")

    # Abnormal status
    ERR_CREATING = EnumField("err_creating", label="unable to create")
    ERR_DELETING = EnumField("err_deleting", label="unable to delete")


# 沙箱默认的 TTL（Time To Live）时长
SANDBOX_DEFAULT_TTL_SECONDS = 30 * 60

# 沙箱 TTL 最大值
SANDBOX_MAX_TTL_SECONDS = 24 * 60 * 60

# 沙箱资源限制的平台默认值（Sandbox.cpu / Sandbox.memory 字段默认值直接引用本常量，保持唯一来源）
# 单位: cpu 为核, memory 为 GB
DEFAULT_SANDBOX_CPU = Decimal(4)
DEFAULT_SANDBOX_MEMORY = Decimal(2)

# 沙箱产物归档 / 下载 URL 的默认与上限有效期(秒)
DEFAULT_DOWNLOAD_URL_EXPIRES_IN = 600
MAX_DOWNLOAD_URL_EXPIRES_IN = 3600
# 上传临时 URL 的有效期，给 daemon 读大文件 + PUT 留足余量
UPLOAD_URL_EXPIRES_IN = 3600
