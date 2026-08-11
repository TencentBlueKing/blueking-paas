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


class SandboxWorkloadType(StrStructuredEnum):
    """Sandbox workload runtime type.

    - DEFAULT: ordinary Kubernetes Pod
    - SANDBOX_INSTANCE: SandboxInstance CR（底层由 sandbox-controller 渲染为 MicroVM）
    """

    DEFAULT = EnumField("default", label="普通 Pod")
    SANDBOX_INSTANCE = EnumField("sandbox_instance", label="SandboxInstance")


# 沙箱默认的 TTL（Time To Live）时长
SANDBOX_DEFAULT_TTL_SECONDS = 30 * 60

# 沙箱 TTL 最大值
SANDBOX_MAX_TTL_SECONDS = 24 * 60 * 60

# 沙箱资源限制的平台默认值（Sandbox.cpu / Sandbox.memory 字段默认值直接引用本常量，保持唯一来源）
# 单位: cpu 为核, memory 为 GB
DEFAULT_SANDBOX_CPU = Decimal(4)
DEFAULT_SANDBOX_MEMORY = Decimal(2)

# 上传临时 URL 的有效期，给 daemon 读大文件 + PUT 留足余量
UPLOAD_URL_EXPIRES_IN = 3600

# bkrepo 临时 token 类型。预览页仅接受 PREVIEW 类型的 token（DOWNLOAD token 会被 bkrepo
# preview 服务直接拒绝），因此不能复用签发下载 URL 的 generic/temporary/url/create
PREVIEW_TOKEN_TYPE = "PREVIEW"

# bkrepo 预览页路由 /ui/{project}/filePreview/{repoType}/{extraParam}/{repo}/{path}
# 中的两个固定段：平台产物仓库均为本地仓库，repoType 取 local；extraParam 仅 remote 仓库
# 需要传 base64 编码的源地址，本地仓库固定为 0
PREVIEW_REPO_TYPE = "local"
PREVIEW_EXTRA_PARAM = "0"
