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


class SandboxDeleteSource(StrStructuredEnum):
    """沙箱删除来源, 指标 ``agent_sandbox_lifetime_seconds`` 的 delete_source 取值."""

    USER = EnumField("user", label="用户主动删除")
    EXPIRED = EnumField("expired", label="过期被清理")


class SandboxCreateFailureReason(StrStructuredEnum):
    """沙箱创建失败原因, 指标 ``agent_sandbox_create_failures_total`` 的 reason 取值."""

    NO_CLUSTER = EnumField("no_cluster", label="没有可用集群")
    IMAGE_VALIDATE = EnumField("image_validate", label="快照镜像校验失败")
    TIMEOUT = EnumField("timeout", label="等待就绪超时")
    K8S_ERROR = EnumField("k8s_error", label="K8s API 调用失败")
    START_FAILED = EnumField("start_failed", label="工作负载启动失败")
    QUOTA_EXCEEDED = EnumField("quota_exceeded", label="超出应用沙箱数量上限")
    ALREADY_EXISTS = EnumField("already_exists", label="同名沙箱已存在")
    VOLUME_INVALID = EnumField("volume_invalid", label="共享卷挂载不合法")
    UNKNOWN = EnumField("unknown", label="其他未归类的原因")


class SandboxOperation(StrStructuredEnum):
    """沙箱接口的操作名, 指标 ``agent_sandbox_requests_total`` 的 operation 取值.

    只覆盖沙箱生命周期与文件/进程接口.
    """

    CREATE = EnumField("create", label="创建沙箱")
    LIST = EnumField("list", label="查询沙箱列表")
    DESTROY = EnumField("destroy", label="销毁沙箱")
    CREATE_FOLDER = EnumField("create_folder", label="创建目录")
    UPLOAD_FILE = EnumField("upload_file", label="上传文件")
    DELETE_FILE = EnumField("delete_file", label="删除文件")
    DOWNLOAD_FILE = EnumField("download_file", label="下载文件")
    EXEC = EnumField("exec", label="执行命令")
    CODE_RUN = EnumField("code_run", label="执行代码")
    LOGS = EnumField("logs", label="读取日志")


class SandboxRequestResult(StrStructuredEnum):
    """接口调用结果, 指标 ``agent_sandbox_requests_total`` 与两个耗时直方图的 result 取值"""

    SUCCESS = EnumField("success", label="成功")
    FAILURE = EnumField("failure", label="失败")


# 沙箱默认的 TTL（Time To Live）时长
SANDBOX_DEFAULT_TTL_SECONDS = 30 * 60

# 沙箱 TTL 最大值
SANDBOX_MAX_TTL_SECONDS = 24 * 60 * 60

# 沙箱资源限制的平台默认值（Sandbox.cpu / Sandbox.memory 字段默认值直接引用本常量，保持唯一来源）
# 单位: cpu 为核, memory 为 GB
DEFAULT_SANDBOX_CPU = Decimal(4)
DEFAULT_SANDBOX_MEMORY = Decimal(2)

# 单个应用可同时存活的沙箱数量上限的平台默认值
# 该值可由 app 级配置 SandboxAppSettings.max_active_sandbox_count 覆盖
DEFAULT_MAX_ACTIVE_SANDBOX_COUNT = 100

# Volume.shared_app_codes 软上限；超出后 share 接口拒绝写入
VOLUME_SHARED_APP_CODES_MAX = 50

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
