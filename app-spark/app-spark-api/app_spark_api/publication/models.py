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

"""发布到开发者中心的两张表：项目与应用的绑定、发布任务。

项目的发布状态（线上版本、最近一次失败、还没看过的结果）都从任务表推出来，不另存一份。
"""

from django.db import models
from django.utils import timezone

from app_spark_api.core.tenant.fields import tenant_id_field_factory
from app_spark_api.publication.constants import PublicationTaskKind, PublicationTaskStatus
from app_spark_api.utils.models import TimestampedModel


class DevCenterAppBinding(TimestampedModel):
    """The developer center application a Project publishes to.

    首次发布时创建应用并写入，之后一直复用。只在创建应用成功之后才写入，所以记录存在就说明开发者中心里确实有这个应用。
    """

    project = models.OneToOneField(
        "projects.Project",
        verbose_name="所属项目",
        on_delete=models.CASCADE,
        related_name="dev_center_app_binding",
    )
    app_code = models.CharField(verbose_name="开发者中心应用 ID", max_length=20, unique=True)
    module_name = models.CharField(verbose_name="发布到的模块", max_length=64)
    tenant_id = tenant_id_field_factory(db_index=False)


class PublicationTaskQuerySet(models.QuerySet["PublicationTask"]):
    """Queries over publication tasks."""

    def pending(self) -> "PublicationTaskQuerySet":
        """Tasks that have not ended yet."""
        return self.filter(status=PublicationTaskStatus.PENDING)

    def finished(self) -> "PublicationTaskQuerySet":
        """Tasks that have ended, latest first."""
        return self.exclude(status=PublicationTaskStatus.PENDING).order_by("-finished_at", "-pk")

    def online(self) -> "PublicationTaskQuerySet":
        """Successful deployments, latest first; the first one is the version serving now."""
        return self.filter(kind=PublicationTaskKind.DEPLOYMENT, status=PublicationTaskStatus.SUCCESSFUL).order_by(
            "-finished_at", "-pk"
        )


class PublicationTask(TimestampedModel):
    """One deployment of a Project.

    发布请求里同步创建应用；打包、上传、提交部署由 Celery 准备任务做，之后由 Celery 轮询结果直到结束，stage 跟着前进。
    同一项目同时最多一个进行中的任务，发起时锁住项目行来保证。
    可选值见 constants：kind 取 PublicationTaskKind，stage 取 PublicationStage，status 取 PublicationTaskStatus。
    """

    project = models.ForeignKey(
        "projects.Project",
        verbose_name="所属项目",
        on_delete=models.CASCADE,
        related_name="publication_tasks",
    )
    kind = models.CharField(verbose_name="任务类型", max_length=16)
    version_id = models.CharField(verbose_name="发布的版本号", max_length=64)
    is_update = models.BooleanField(verbose_name="发起时是否已有线上版本", default=False)
    operator = models.CharField(verbose_name="发起人用户名", max_length=64)
    stage = models.CharField(verbose_name="当前步骤", max_length=16)
    status = models.CharField(verbose_name="任务状态", max_length=16, default=PublicationTaskStatus.PENDING.value)

    # 准备任务开始时写入，只有写成功的那条消息去做，重复投递、worker 崩溃后的重投都会被挡住。
    prepare_started_at = models.DateTimeField(verbose_name="准备任务开始的时间", null=True, blank=True)
    # 发出部署请求前写入。有它而没有 deployment_id，说明部署可能已经生效、只是没记下，不能再发一次。
    deploy_requested_at = models.DateTimeField(verbose_name="发出部署请求的时间", null=True, blank=True)
    deployment_id = models.CharField(verbose_name="开发者中心部署 ID", max_length=64, blank=True, default="")
    # 部署超时从这里算。
    deploy_submitted_at = models.DateTimeField(verbose_name="提交部署的时间", null=True, blank=True)
    # 每轮轮询都是一次独立的 Celery 任务，下面两个状态只能落库。
    last_polled_at = models.DateTimeField(verbose_name="最近一次查询部署结果的时间", null=True, blank=True)
    access_url_polls = models.PositiveSmallIntegerField(verbose_name="成功后等待访问地址的轮数", default=0)

    access_url = models.CharField(verbose_name="部署成功后的访问地址", max_length=512, blank=True, default="")
    error = models.TextField(verbose_name="失败原因", blank=True, default="")
    # 结果页只展示一次：用户确认看过、或在发布请求里当场看到了失败原因时为 True。
    result_seen = models.BooleanField(verbose_name="结果是否已看过", default=False)
    started_at = models.DateTimeField(verbose_name="发起时间", default=timezone.now)
    finished_at = models.DateTimeField(verbose_name="结束时间", null=True, blank=True)
    tenant_id = tenant_id_field_factory(db_index=False)

    objects = PublicationTaskQuerySet.as_manager()
