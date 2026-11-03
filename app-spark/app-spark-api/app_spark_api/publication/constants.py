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

"""发布任务的取值与时间参数。

模型字段不用 choices，可选值以这里为准（取值以后可能增加，比如下架任务）。
"""

from datetime import timedelta
from enum import StrEnum


class PublicationTaskKind(StrEnum):
    """What a task does to the application in the developer center."""

    DEPLOYMENT = "deployment"


class PublicationStage(StrEnum):
    """The step a deployment task is on, in the order they run."""

    BINDING = "binding"
    PACKAGING = "packaging"
    UPLOADING = "uploading"
    DEPLOYING = "deploying"


class PublicationTaskStatus(StrEnum):
    """Where a task has got to, named like the developer center's deployment statuses."""

    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"


# 开发者中心应用名称的长度上限。名称里它不认的字符（如空格）由开发者中心自己去掉。
APP_NAME_MAX_LENGTH = 20
# 查询部署结果的间隔秒数。
DEPLOY_POLL_INTERVAL_SECONDS = 3
# 已提交部署的任务超过这么久没被查过，就认为轮询消息丢了（如投递时队列不可用、worker 崩溃），重新投递。
POLL_STALL_AFTER = timedelta(seconds=60)
# 从发起算起，超过这么久还没提交部署，说明发布请求或准备任务的进程中途没了（如 Pod 重启），或者队列一直
# 不可用。不自动重做（打包本身可能就是把 worker 拖垮的原因），任务判失败，免得项目一直卡在进行中。
PREPARE_TIMEOUT = timedelta(minutes=10)
# 发出部署请求超过这么久还没记下部署 ID，就认为发请求的 worker 中途没了。要比客户端的单次请求超时（60 秒）长，
# 否则会把还在等响应的部署判失败。
DEPLOY_REQUEST_TIMEOUT = timedelta(minutes=2)
# 轮询任务本身出了意外（多半是数据库抖动；开发者中心的网络错误、5xx 由轮询自己按间隔重试），过这么久再查。
POLL_RETRY_COUNTDOWN_SECONDS = 10
# 上面这种重试最多几次（约 5 分钟）。一直失败的交给查询发布状态时的兜底，部署超时后判失败。
POLL_MAX_RETRIES = 30
# 部署成功但开发者中心还没给出访问地址时，再多查几轮。地址一般随成功一起返回，偶尔晚一点。
MAX_POLLS_FOR_ACCESS_URL = 3
# 从提交部署算起，超过这么久还没结束就判失败。
DEPLOY_TIMEOUT = timedelta(minutes=15)
