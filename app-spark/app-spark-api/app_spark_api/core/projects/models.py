from django.db import models

from app_spark_api.core.tenant.fields import tenant_id_field_factory
from app_spark_api.utils.models import BkUserField, OwnerTimestampedModel


class ProjectManager(models.Manager):
    """Manager for Projects"""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Project(OwnerTimestampedModel):
    """app-spark 的 Project 是开发者通过自然语言开发的 SaaS 项目，可以被发布到蓝鲸运营系统 PaaS 平台。

    * 为了避免和 PaaS 平台的 Application 名字冲突，app-spark 有意使用了“项目”而非“应用”。
    """

    id = models.CharField(verbose_name="项目 ID", max_length=20, primary_key=True)
    name = models.CharField(verbose_name="项目名称", max_length=20)
    creator = BkUserField()
    is_deleted = models.BooleanField("是否删除", default=False)

    tenant_id = tenant_id_field_factory(db_index=False)

    objects = ProjectManager()
    # 需要访问全量数据（含已软删除项目）时使用本管理器，例如数据订正、管理后台等场景
    default_objects = models.Manager()

    class Meta:
        # 项目名称租户内唯一
        # TODO: 软删除后应该释放对应的 name
        unique_together = ("tenant_id", "name")
