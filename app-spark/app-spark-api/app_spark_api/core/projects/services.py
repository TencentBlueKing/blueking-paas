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
import logging
import secrets
import string

import attrs
from asgiref.sync import sync_to_async
from django.db import IntegrityError, transaction

from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.services import (
    aclose_project_conversations,
    adelete_project_conversations,
    create_conversation,
)
from app_spark_api.agent.runtime.exceptions import AgentResourceDeletionError
from app_spark_api.agent.runtime.factory import get_agent_runtime_provider
from app_spark_api.core.projects import constants
from app_spark_api.core.projects.exceptions import (
    ProjectAlreadyDeletedError,
    ProjectDeletionError,
    ProjectIdTakenError,
)
from app_spark_api.core.projects.models import Project
from app_spark_api.core.projects.signals import project_deleting
from app_spark_api.repository.git.services import adelete_project_repository, aprovision_project_repository
from app_spark_api.repository.git.source_packages import adelete_project_source_packages

logger = logging.getLogger(__name__)

_GENERATED_ID_ALPHABET = string.ascii_lowercase + string.digits


@attrs.frozen
class PromptProjectCreation:
    """从一句话建出来的东西：Project 和承接第一轮对话的会话。

    :param project: 已落库的 Project。
    :param conversation: 已落库、尚未拉起 Runtime 的会话。
    """

    project: Project
    conversation: Conversation


async def create_project(
    *, project_id: str, name: str, owner: str, tenant_id: str, initial_prompt: str = ""
) -> Project:
    """建一个 Project，owner 与 creator 都记为 ``owner``。

    :param project_id: 项目 ID，必须已经按 ``PROJECT_ID_PATTERN`` 校验过。
    :param name: 项目名称，不要求唯一。
    :param owner: 建项目的用户 pk。
    :param tenant_id: 项目所属租户。
    :param initial_prompt: 从一句话创建时的那句话；手动创建时留空。
    :return: 已经落库的 Project。
    :raises ProjectIdTakenError: ID 已被占用。
    """
    await _reject_id_taken(project_id)

    try:
        project = await sync_to_async(_insert)(
            project_id=project_id,
            name=name,
            owner=owner,
            tenant_id=tenant_id,
            initial_prompt=initial_prompt,
        )
    except IntegrityError:
        # 上面查过了还是撞，那就只有一种情况：在检查和插入之间有人抢先把同一个 ID 建成了。
        # 主键约束是这里真正的保证，前面那次检查只负责把话说清楚。
        await _reject_id_taken(project_id)
        raise

    # 建仓在事务外：远端失败必须留下 Project 和 failed 状态，而不是把刚建成的行回滚掉。
    await aprovision_project_repository(project)
    return project


async def create_project_from_prompt(*, content: str, owner: str, tenant_id: str) -> PromptProjectCreation:
    """用用户的第一句话建一个 Project，并为它开好第一个会话。

    ID 由服务端生成，名称暂时就用 ID，之后交给自动命名去改。这句话会记到 Project 上，但不会在
    这里发给 Agent：第一轮对话仍由客户端拿着返回的会话编号走 runs 接口，和手动建项目之后发的
    第一句话是同一条路径。会话也只建行、不拉 Runtime，那几十秒留给 runs 去付。

    自动命名不在这里启动：它要用调用方请求里的用户登录态换 access_token，那只有 API 层拿得到。
    调用方建完项目后应调用 ``tasks.start_int_renaming``。

    Example::

        created = await create_project_from_prompt(content="做一个番茄钟", owner=user.pk, tenant_id="default")
        # 随后客户端调用 POST /projects/{created.project.id}/conversations/{created.conversation.number}/runs/

    :param content: 用户的第一句话。
    :param owner: 建项目的用户 pk。
    :param tenant_id: 项目所属租户。
    :return: 建好的 Project 与会话。
    :raises ProjectIdTakenError: 连续几次生成的 ID 都已被占用。实际上不会发生。
    """
    for attempt in range(1, constants.GENERATED_PROJECT_ID_MAX_ATTEMPTS + 1):
        project_id = generate_project_id()
        try:
            project = await create_project(
                project_id=project_id,
                name=project_id,
                owner=owner,
                tenant_id=tenant_id,
                initial_prompt=content,
            )
        except ProjectIdTakenError:
            if attempt == constants.GENERATED_PROJECT_ID_MAX_ATTEMPTS:
                raise
            logger.warning("Generated project id %s is taken, generating another one", project_id)
            continue
        break

    conversation = await create_conversation(project, owner=owner)
    return PromptProjectCreation(project=project, conversation=conversation)


def generate_project_id() -> str:
    """生成一个符合 ``PROJECT_ID_PATTERN`` 的随机项目 ID，例如 ``p-k3x9q0m2ab``。"""
    suffix = "".join(
        secrets.choice(_GENERATED_ID_ALPHABET) for _ in range(constants.GENERATED_PROJECT_ID_SUFFIX_LENGTH)
    )
    return f"{constants.GENERATED_PROJECT_ID_PREFIX}{suffix}"


async def _reject_id_taken(project_id: str) -> None:
    """ID 已被占用就直接拒掉。ID 是全局唯一的，不分租户，因此软删除的项目也仍占着它。

    :raises ProjectIdTakenError: ID 已被占用。
    """
    if await Project.default_objects.filter(pk=project_id).aexists():
        raise ProjectIdTakenError(f"Project id {project_id} is already taken")


async def rename_project(project: Project, *, name: str) -> Project:
    """把 Project 改名为 ``name``。

    名称只是展示用的标签，不要求唯一，改成当前名称也不算冲突，直接原样返回。名称只影响展示：
    仓库等外部资源以项目 ID 命名，不需要同步。

    :param project: 要改名的 Project，调用方负责确认它对当前用户可见。
    :param name: 新名称，长度必须已经校验过。
    :return: 改名后的 Project，字段已从数据库刷新。
    :raises ProjectAlreadyDeletedError: Project 在取出之后被并发删除了。
    """
    if name == project.name:
        return project

    changed = await Project.objects.arename(project.pk, name)
    if not changed:
        raise ProjectAlreadyDeletedError

    await project.arefresh_from_db()
    # 刷新走基础管理器，能读到软删除行：更新成功之后、刷新之前被并发删除，也按已删除处理。
    if project.is_deleted:
        raise ProjectAlreadyDeletedError
    return project


async def delete_project(project: Project) -> None:
    """Delete every located Project resource before hiding the Project itself."""
    current_category = "background task"

    try:
        async with asyncio.timeout(constants.DELETE_PROJECT_TIMEOUT_SECONDS):
            # 先让挂在项目上的后台任务（如发布）收手，否则清理期间它们还会动这个项目。receiver 自己说明失败类别。
            try:
                await project_deleting.asend(sender=Project, project=project)
            except ProjectDeletionError:
                raise
            except Exception as exc:
                raise ProjectDeletionError(current_category) from exc

            current_category = "conversation"
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

            # 放在仓库之后：远端仓库没了，就不会再有发布把新的包传上来。
            current_category = "source package"
            try:
                await adelete_project_source_packages(project.pk)
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


def _insert(*, project_id: str, name: str, owner: str, tenant_id: str, initial_prompt: str) -> Project:
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
            initial_prompt=initial_prompt,
        )
