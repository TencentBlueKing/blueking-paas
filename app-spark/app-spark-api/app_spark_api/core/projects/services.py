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

"""创建新的 Project。"""

from __future__ import annotations

import asyncio

from asgiref.sync import sync_to_async
from django.db import IntegrityError, transaction

from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.services import (
    aclose_project_conversations,
    adelete_project_conversations,
)
from app_spark_api.agent.runtime.exceptions import AgentResourceDeletionError
from app_spark_api.agent.runtime.factory import get_agent_runtime_provider
from app_spark_api.core.projects import constants
from app_spark_api.core.projects.exceptions import (
    ProjectAlreadyDeletedError,
    ProjectDeletionError,
    ProjectIdTakenError,
    ProjectNameTakenError,
)
from app_spark_api.core.projects.models import Project
from app_spark_api.repository.git.services import adelete_project_repository, aprovision_project_repository


async def create_project(*, project_id: str, name: str, owner: str, tenant_id: str) -> Project:
    """建一个 Project，owner 与 creator 都记为 ``owner``。

    :param project_id: 项目 ID，必须已经按 ``PROJECT_ID_PATTERN`` 校验过。
    :param name: 项目名称。
    :param owner: 建项目的用户 pk。
    :param tenant_id: 项目所属租户。
    :return: 已经落库的 Project。
    :raises ProjectIdTakenError: ID 已被占用。
    :raises ProjectNameTakenError: 同租户下已有同名项目。
    """
    await _reject_taken(project_id=project_id, name=name, tenant_id=tenant_id)

    try:
        project = await sync_to_async(_insert)(
            project_id=project_id,
            name=name,
            owner=owner,
            tenant_id=tenant_id,
        )
    except IntegrityError:
        # 上面查过了还是撞，那就只有一种情况：在检查和插入之间有人抢先把同一个 ID 或名称建成了。
        # 唯一约束是这里真正的保证，前面那次检查只负责把话说清楚。
        await _reject_taken(project_id=project_id, name=name, tenant_id=tenant_id)
        raise

    # 建仓在事务外：远端失败必须留下 Project 和 failed 状态，而不是把刚建成的行回滚掉。
    await aprovision_project_repository(project)
    return project


async def _reject_taken(*, project_id: str, name: str, tenant_id: str) -> None:
    """ID 或名称已被占用就直接拒掉，并说清楚是哪一个。

    项目 ID 用 ``default_objects`` 查，因为软删除行仍占着主键。名称只查活跃项目：
    软删除会把名称置空，同一租户可以重新使用原名称。

    :raises ProjectIdTakenError: ID 已被占用。ID 是全局唯一的，不分租户。
    :raises ProjectNameTakenError: 同租户下已有同名项目。
    """
    if await Project.default_objects.filter(pk=project_id).aexists():
        raise ProjectIdTakenError(f"Project id {project_id} is already taken")

    if await Project.objects.filter(tenant_id=tenant_id, name=name).aexists():
        raise ProjectNameTakenError(f"Project name {name} is already taken in tenant {tenant_id}")


async def delete_project(project: Project) -> None:
    """Delete every located Project resource before hiding the Project itself."""
    current_category = "conversation"

    try:
        async with asyncio.timeout(constants.DELETE_PROJECT_TIMEOUT_SECONDS):
            # 先结束活跃会话，否则 Runtime 停掉后还能被新的一轮重新拉起来。
            try:
                await aclose_project_conversations(project.pk)
            except Exception as exc:
                raise ProjectDeletionError(current_category) from exc

            conversation_ids = [
                str(conversation_id)
                async for conversation_id in Conversation.objects.filter(project=project).values_list("id", flat=True)
            ]

            current_category = "sandbox"
            try:
                provider = get_agent_runtime_provider()
                await provider.delete_project_resources(project.pk, conversation_ids)
            except AgentResourceDeletionError as exc:
                raise ProjectDeletionError(exc.category) from exc
            except Exception as exc:
                # 内置 provider 会给出更精确的类别；未知 provider 的运行环境统一按沙箱对外描述。
                raise ProjectDeletionError(current_category) from exc

            current_category = "context file"
            try:
                await adelete_project_conversations(project.pk)
            except Exception as exc:
                raise ProjectDeletionError(current_category) from exc

            current_category = "repository"
            try:
                await adelete_project_repository(project)
            except Exception as exc:
                raise ProjectDeletionError(current_category) from exc

            current_category = "project record"
            try:
                changed = await Project.objects.asoft_delete(project.pk)
            except Exception as exc:
                raise ProjectDeletionError(current_category) from exc

            # 并发请求已经完成最终切换时，本请求按「已删除项目不可见」返回统一 404。
            if not changed:
                raise ProjectAlreadyDeletedError
    except TimeoutError as exc:
        raise ProjectDeletionError(current_category) from exc


def _insert(*, project_id: str, name: str, owner: str, tenant_id: str) -> Project:
    """把 Project 落库。同步，因为要开事务，而 Django 的异步 ORM 没有自己的事务。"""
    # 放在事务里，是为了让 Project 和它的会话计数器一起成立：计数器行由 post_save signal
    # 建（见 conversations.signals），没有事务的话，signal 挂掉就会留下一个永远开不出会话
    # 的 Project。
    with transaction.atomic():
        return Project.objects.create(
            id=project_id,
            name=name,
            creator=owner,
            owner=owner,
            tenant_id=tenant_id,
        )
