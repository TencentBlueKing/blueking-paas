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

"""发布的各个步骤，按执行顺序各占一个模块，以及驱动它们的地方。

1. binding：发布请求里由 services.start_deployment 调 bind_app，首次发布时创建应用，阶段推进到 packaging。
   创建应用很快，放在请求里，失败原因当场告诉用户。
2. preparing：Celery 准备任务（tasks.prepare_publication_deployment）调 prepare_deployment，打包、上传并提交部署。
   这几步可能要几分钟，所以交给 Celery。
3. polling：提交成功后由 tasks.DeploymentPoller 反复调 poll_deployment，部署结束时写下结果。

重做是否安全决定了各步怎么防重复：创建应用之前先查绑定；打包和上传重做也安全，只有提交部署不能发两次，
所以准备任务只做一次；轮询只读，只有写下结果要保证只生效一次。

progress 是各步共用的状态写入（推进阶段、写下结果），errors 是给用户看的失败原因。
"""

from app_spark_api.publication.steps.binding import bind_app
from app_spark_api.publication.steps.errors import (
    MSG_APP_NOT_MANAGED,
    MSG_BKPAAS_UNAVAILABLE,
    MSG_DEPLOY_UNCERTAIN,
    MSG_MODULE_NOT_DEFAULT,
    MSG_NOT_AUTHORIZED,
    MSG_NOT_CONFIGURED,
    MSG_POLL_FAILED,
    MSG_PREPARE_FAILED,
    MSG_PREPARE_INTERRUPTED,
    MSG_PROJECT_DELETED,
    FailureCause,
    PublicationStepError,
    make_deploy_timeout_message,
    to_step_error,
)
from app_spark_api.publication.steps.polling import PollOutcome, poll_deployment
from app_spark_api.publication.steps.preparing import prepare_deployment
from app_spark_api.publication.steps.progress import FinishGuard, afail_task_by_id, afinish_task

__all__ = [
    "MSG_APP_NOT_MANAGED",
    "MSG_BKPAAS_UNAVAILABLE",
    "MSG_DEPLOY_UNCERTAIN",
    "MSG_MODULE_NOT_DEFAULT",
    "MSG_NOT_AUTHORIZED",
    "MSG_NOT_CONFIGURED",
    "MSG_POLL_FAILED",
    "MSG_PREPARE_FAILED",
    "MSG_PREPARE_INTERRUPTED",
    "MSG_PROJECT_DELETED",
    "FailureCause",
    "FinishGuard",
    "PollOutcome",
    "PublicationStepError",
    "afail_task_by_id",
    "afinish_task",
    "bind_app",
    "make_deploy_timeout_message",
    "poll_deployment",
    "prepare_deployment",
    "to_step_error",
]
