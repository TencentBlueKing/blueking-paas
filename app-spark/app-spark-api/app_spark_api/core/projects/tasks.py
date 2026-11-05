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

"""Project 的后台任务：派发、worker 入口，以及任务自己失败时的兜底记录。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync, sync_to_async
from celery import shared_task

from app_spark_api.agent.runtime.model_access import fetch_bkaidev_access_token
from app_spark_api.core.projects import int_renaming
from app_spark_api.core.projects.models import Project, ProjIntRenaming
from app_spark_api.ext.llm import build_llm_client, requires_access_token

if TYPE_CHECKING:
    from app_spark_api.infras.bk_access_token import UserCredential

logger = logging.getLogger(__name__)

# 换 token、投递或起名没能开始时的统一说法。具体原因只进日志：其中可能有网关地址、队列凭据等
# 不适合写给用户的信息。
START_FAILED_MESSAGE = "Renaming could not be started."


async def start_int_renaming(project: Project, *, credential: UserCredential | None) -> None:
    """给一个刚建好的项目排一次自动命名。

    先落一条 pending 记录，前端立刻就能轮询到；然后换 token 并投递 Celery 任务。整个过程视为一件事，
    任何一步失败都只把记录标成 failed，不向调用方抛异常——项目已经建好了，命名失败不该把它回滚掉。

    Example::

        created = await services.create_project_from_prompt(...)
        await tasks.start_int_renaming(created.project, credential=get_user_credential(request))

    :param project: 要命名的项目，名称此时还是占位 ID。
    :param credential: 调用方的蓝鲸登录态；走 bkaidev 网关时用它换 access_token。
    """
    try:
        await ProjIntRenaming.objects.aget_or_create(project_id=project.pk)
        access_token = await fetch_bkaidev_access_token(credential) if requires_access_token() else None
        # Celery 的投递是同步网络操作，在事件循环里直接调用会占住 worker。
        await sync_to_async(rename_project_from_prompt.apply_async, thread_sensitive=False)(
            args=(project.pk, access_token),
        )
    except Exception:
        logger.exception("Starting int renaming for project %s failed", project.pk)
        await _record_failure(project.pk, START_FAILED_MESSAGE)


@shared_task(name="projects.rename_project_from_prompt")
def rename_project_from_prompt(project_id: str, access_token: str | None = None) -> None:
    """Celery 任务入口：在 worker 里构造模型客户端，然后执行命名。

    :param project_id: 要命名的项目。
    :param access_token: 走 bkaidev 网关时需要，由建项目的请求换好；其它来源为 None。
    """
    async_to_sync(arename_project_from_prompt)(project_id, access_token=access_token)


async def arename_project_from_prompt(project_id: str, *, access_token: str | None) -> None:
    try:
        llm = build_llm_client(access_token=access_token)
    except Exception:
        logger.exception("Building the LLM client for naming project %s failed", project_id)
        await _record_failure(project_id, START_FAILED_MESSAGE)
        return

    await int_renaming.run(project_id, llm=llm)


async def _record_failure(project_id: str, message: str) -> None:
    """尽力把任务标成失败；记录本身写不进去时也不能再抛。"""
    try:
        record = await ProjIntRenaming.objects.filter(project_id=project_id).afirst()
        if record is not None:
            await record.fail(message)
    except Exception:
        logger.exception("Recording the int-renaming failure for project %s failed", project_id)
