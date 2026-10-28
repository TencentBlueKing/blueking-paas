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
from django.db.models import F
from django.utils import timezone

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
        """把一个活跃 Project 标记为已删除，并释放它的名称。

        :param project_id: 要删除的 Project。
        :return: 是否由本次调用完成了删除。Project 不存在或已被删除时返回 ``False``。
        """
        now = timezone.now()

        # MySQL 按 SET 顺序从左到右求值，name_at_deletion 必须排在 name 之前。
        changed = await self.filter(pk=project_id).aupdate(
            is_deleted=True,
            name_at_deletion=F("name"),
            name=None,
            updated_at=now,
        )

        return bool(changed)

    async def arename(self, project_id: str, name: str) -> bool:
        """修改一个活跃 Project 的名称。

        名称在租户内的唯一性由 ``unique_together`` 保证，撞上时抛出 ``IntegrityError``，由调用方翻译。

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
    # 已删除项目把名称置空以释放租户内唯一约束。MySQL 的唯一索引允许多行 NULL，
    # 因此同一租户可以留下多个软删除项目，同时不必改成数据库不支持的条件唯一索引。
    name = models.CharField(verbose_name="项目名称", max_length=20, null=True)
    # 删除前的名称，只作记录，不参与唯一约束。
    name_at_deletion = models.CharField(verbose_name="删除前的项目名称", max_length=20, blank=True, default="")
    creator = BkUserField()
    is_deleted = models.BooleanField("是否删除", default=False)

    tenant_id = tenant_id_field_factory(db_index=False)

    objects = ProjectManager()
    # 需要访问全量数据（含已软删除项目）时使用本管理器，例如数据订正、管理后台等场景
    default_objects = models.Manager()

    class Meta:
        # 活跃项目的名称非空，因此这个约束仍保证它们在租户内唯一；软删除行统一存 NULL。
        unique_together = ("tenant_id", "name")
