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

"""Project 与远端 Git 仓库的一对一关联，以及从仓库打出的源码包。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from blue_krill.models.fields import EncryptField
from django.db import models
from django.utils import timezone

from app_spark_api.core.tenant.fields import tenant_id_field_factory
from app_spark_api.repository.git.constants import DEFAULT_BRANCH, REPOSITORY_ERROR_DETAIL, STATUS_PENDING
from app_spark_api.utils.models import TimestampedModel

if TYPE_CHECKING:
    from datetime import datetime


class ProjectGitRepository(TimestampedModel):
    """One private Git repository for one Project, plus the long-lived write token."""

    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="git_repository",
    )
    remote_id = models.BigIntegerField(null=True, blank=True, help_text="远端仓库数字 ID")
    owner = models.CharField(max_length=64, help_text="远端组织名")
    name = models.CharField(max_length=64, help_text="远端仓库名，与 Project ID 相同")
    default_branch = models.CharField(max_length=64, default=DEFAULT_BRANCH)
    status = models.CharField(max_length=16, default=STATUS_PENDING)
    status_detail = models.TextField(blank=True, default="")
    write_token = EncryptField(null=True, blank=True, help_text="仓库范围的读写 token 明文（加密存储）")
    write_token_id = models.PositiveIntegerField(null=True, blank=True, help_text="远端 token ID，用于撤销")
    clone_url = models.CharField(max_length=512, blank=True, default="")

    @property
    def has_remote_repository(self) -> bool:
        """Whether the remote repository exists, which is all a *read* needs."""
        return self.remote_id is not None

    @property
    def public_status_detail(self) -> str:
        """Return a safe summary, including for rows containing legacy errors."""
        # Older rows may contain remote response bodies or internal URLs. Only
        # pass through known safe messages; substring redaction is too fragile.
        if self.status_detail in {"", "credentials revoked"}:
            return self.status_detail
        return REPOSITORY_ERROR_DETAIL


class ProjectSourcePackageQuerySet(models.QuerySet["ProjectSourcePackage"]):
    """ProjectSourcePackage 的查询集。"""

    def unused_since(self, cutoff: datetime) -> ProjectSourcePackageQuerySet:
        """只留下从 ``cutoff`` 起就再没被使用过的包，也就是可以回收的那些。

        :param cutoff: 截止时间，``last_used_at`` 早于它的包算作没人用。
        """
        return self.filter(last_used_at__lt=cutoff)


class ProjectSourcePackage(TimestampedModel):
    """某个 commit 的源码被打成 tgz、上传到蓝鲸制品库的一条记录。

    以 commit SHA 而不是分支或 tag 区分：主分支会被反复发布，同一个名字在不同时刻指向不同的
    内容，只有 SHA 能唯一确定一份源码。反过来，同一个 SHA 不论经由主分支还是 tag 选中，打出来
    的都是同一份包，所以每个 Project 的每个 SHA 只上传一次，后来者复用这一行。

    包不会永久保存：``last_used_at`` 记着它最近一次被交出去（上传、复用或签下载地址）的时间，
    长期没人用的包由 ``delete_unused_source_packages`` 命令回收，见
    :func:`~app_spark_api.repository.git.source_packages.delete_unused_source_packages`。
    """

    project = models.ForeignKey(
        "projects.Project",
        verbose_name="所属项目",
        on_delete=models.CASCADE,
        related_name="source_packages",
    )
    # 仅作记录，不参与任何查询：Project 以后若换了 Git 仓库，靠它分辨一个包是从哪个仓库打出来的。
    repo_full_name = models.CharField(verbose_name="打包时的仓库全名，如 org/name", max_length=255)
    # 64 而不是 40：Forgejo 也支持 SHA-256 对象格式的仓库。
    commit_sha = models.CharField(verbose_name="源码所在 commit 的完整 SHA", max_length=64)
    bucket = models.CharField(verbose_name="制品库通用仓库名", max_length=128)
    key = models.CharField(verbose_name="制品库中的对象路径", max_length=512)
    size = models.PositiveBigIntegerField(verbose_name="包大小（字节）")
    last_used_at = models.DateTimeField(verbose_name="最近一次被使用的时间", default=timezone.now)
    tenant_id = tenant_id_field_factory()

    objects = ProjectSourcePackageQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "commit_sha"], name="uniq_source_package_per_commit"),
        ]
        # 回收按它扫全表，见 ProjectSourcePackageQuerySet.unused_since。
        indexes = [models.Index(fields=["last_used_at"])]

    def mark_used(self) -> bool:
        """记下这个包刚被交出去（复用或签下载地址），使它不会被回收。

        用条件 UPDATE 而不是 ``save()``：回收正锁着这一行时它会等，等到的若是行已被删，就如实报告
        「不存在」，而不是悄悄把它重新插回去。

        :return: 是否记上了。``False`` 表示这个包刚被回收，调用方应当重新上传。
        """
        now = timezone.now()
        if not type(self).objects.filter(pk=self.pk).update(last_used_at=now):
            return False
        self.last_used_at = now
        return True
