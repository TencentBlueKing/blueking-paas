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

from django.db import models
from django.utils import timezone

from app_spark_api.core.projects.constants import PROJECT_NAME_MAX_LENGTH, IntRenamingStatus
from app_spark_api.core.tenant.fields import tenant_id_field_factory
from app_spark_api.utils.models import BkUserField, OwnerTimestampedModel


class ProjectManager(models.Manager["Project"]):
    """Manager for Projects"""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def owned_by(self, owner: str, *, tenant_id: str) -> "models.QuerySet[Project]":
        """列出某个用户自己的 Project，按创建时间倒序。

        软删除的项目不会出现，这由本管理器的 ``get_queryset()`` 负责。

        :param owner: 项目 owner 的用户 pk。
        :param tenant_id: 限定的租户。
        :return: 排好序、尚未取值的 queryset，翻页交给调用方。
        """
        return self.filter(owner=owner, tenant_id=tenant_id).order_by("-created_at", "id")

    async def asoft_delete(self, project_id: str) -> bool:
        """把一个活跃 Project 标记为已删除。

        :param project_id: 要删除的 Project。
        :return: 是否由本次调用完成了删除。Project 不存在或已被删除时返回 ``False``。
        """
        changed = await self.filter(pk=project_id).aupdate(is_deleted=True, updated_at=timezone.now())
        return bool(changed)

    async def arename(self, project_id: str, name: str) -> bool:
        """修改一个活跃 Project 的名称。

        :param project_id: 要改名的 Project。
        :param name: 新名称。
        :return: 是否改到了行。Project 不存在或已被删除时返回 ``False``。
        """
        changed = await self.filter(pk=project_id).aupdate(name=name, updated_at=timezone.now())
        return bool(changed)


class Project(OwnerTimestampedModel):
    """app-spark 的 Project 是开发者通过自然语言开发的 SaaS 项目，可以被发布到蓝鲸运营系统 PaaS 平台。

    * 为了避免和 PaaS 平台的 Application 名字冲突，app-spark 有意使用了“项目”而非“应用”。
    """

    id = models.CharField(verbose_name="项目 ID", max_length=20, primary_key=True)
    # 展示用的名称，不要求唯一：两个项目可以取同一个名字，自动命名也不必为了避让而加后缀。
    name = models.CharField(verbose_name="项目名称", max_length=PROJECT_NAME_MAX_LENGTH)
    # 从一句话创建时用户发的那句话，手动创建的项目为空。第一轮对话仍由客户端照常经 runs 接口发出，
    # 这里只是留底：客户端没来得及发出去（比如页面刷新）时可以拿回来，之后的自动命名也要读它。
    initial_prompt = models.TextField(verbose_name="创建项目时的第一句话", blank=True, default="")
    creator = BkUserField()
    is_deleted = models.BooleanField("是否删除", default=False)

    tenant_id = tenant_id_field_factory(db_index=False)

    objects = ProjectManager()
    # 需要访问全量数据（含已软删除项目）时使用本管理器，例如数据订正、管理后台等场景
    default_objects = models.Manager()


class ProjIntRenaming(models.Model):
    """给从一句话创建的项目自动起名的结果，一个项目最多一行。

    ``name`` 为空是正常结果：描述不足以起名时模型会明确留空，调用方保留项目原来的名字即可。

    是否结束看时间字段，两者都为空表示任务还在排队或执行：
    - ``completed_at`` 有值：正常结束，``name`` 是最终结论（可以为空）；
    - ``error_at`` 有值：执行失败，``error_msg`` 说明原因。
    """

    # 失败原因要展示给用户，也可能被贴进工单里，截断到一段合理的长度。
    ERROR_MESSAGE_MAX_LENGTH = 2000

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="int_renaming",
        verbose_name="所属项目",
    )
    name = models.CharField(verbose_name="生成的项目名称", max_length=PROJECT_NAME_MAX_LENGTH, null=True)
    completed_at = models.DateTimeField(verbose_name="完成时间", null=True)
    error_at = models.DateTimeField(verbose_name="失败时间", null=True)
    error_msg = models.TextField(verbose_name="失败原因", blank=True, default="")

    class Meta:
        constraints = [
            # 一次任务只有一个结局，防止「既完成又失败」这种自相矛盾的行被写进来。
            models.CheckConstraint(
                condition=models.Q(completed_at__isnull=True) | models.Q(error_at__isnull=True),
                name="projects_projintrenaming_at_most_one_outcome",
            ),
        ]

    @property
    def is_finished(self) -> bool:
        """任务是否已经有结论（不论成功还是失败）。"""
        return self.completed_at is not None or self.error_at is not None

    @property
    def status(self) -> IntRenamingStatus:
        """当前状态，供 API 直接读出。"""
        if self.completed_at is not None:
            return IntRenamingStatus.COMPLETED
        if self.error_at is not None:
            return IntRenamingStatus.FAILED
        return IntRenamingStatus.PENDING

    async def complete(self, name: str | None) -> None:
        """把一次成功的命名写进记录，并在项目名仍是占位 ID 时更新项目。

        :param name: 生成的名字；模型认为描述不足以起名时为 None。
        """
        now = timezone.now()
        # 已经有了结论的记录不再改写。用条件更新代替加锁，重复执行也只会成功一次。
        changed = (
            await type(self)
            .objects.filter(pk=self.pk, completed_at__isnull=True, error_at__isnull=True)
            .aupdate(name=name, completed_at=now)
        )
        if not changed:
            return

        if name:
            # 只改还挂着占位 ID 的项目：用户在后台任务跑完前手动改过名的话，保留用户的名字。
            await Project.objects.filter(pk=self.project_id, name=self.project_id).aupdate(name=name, updated_at=now)

    async def fail(self, message: str) -> None:
        """把一次失败写进记录；已经有结论的记录不再改写。

        :param message: 失败原因，过长会被截断。
        """
        await (
            type(self)
            .objects.filter(pk=self.pk, completed_at__isnull=True, error_at__isnull=True)
            .aupdate(error_at=timezone.now(), error_msg=message[: self.ERROR_MESSAGE_MAX_LENGTH])
        )
