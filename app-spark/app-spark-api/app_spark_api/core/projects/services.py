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

from asgiref.sync import sync_to_async
from django.db import IntegrityError, transaction

from app_spark_api.core.projects.exceptions import ProjectIdTakenError, ProjectNameTakenError
from app_spark_api.core.projects.models import Project


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
        return await sync_to_async(_insert)(
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


async def _reject_taken(*, project_id: str, name: str, tenant_id: str) -> None:
    """ID 或名称已被占用就直接拒掉，并说清楚是哪一个。

    用 ``default_objects`` 而不是 ``objects``：软删除的 Project 仍然占着主键和
    ``(tenant_id, name)`` 唯一约束，查占用时必须把它们也算进去。

    :raises ProjectIdTakenError: ID 已被占用。ID 是全局唯一的，不分租户。
    :raises ProjectNameTakenError: 同租户下已有同名项目。
    """
    if await Project.default_objects.filter(pk=project_id).aexists():
        raise ProjectIdTakenError(f"Project id {project_id} is already taken")
    if await Project.default_objects.filter(tenant_id=tenant_id, name=name).aexists():
        raise ProjectNameTakenError(f"Project name {name} is already taken in tenant {tenant_id}")


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
