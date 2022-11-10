# -*- coding: utf-8 -*-
from django.db import models  # noqa
from paas_service.models import AuditedModel


class ApmData(AuditedModel):
    bk_app_code = models.CharField("蓝鲸应用ID", max_length=64)
    env = models.CharField("环境", max_length=64)
    app_name = models.CharField("APM应用名称", max_length=64)
    data_token = models.CharField("在监控申请的token", max_length=255)
    is_delete = models.BooleanField("是否已经被删除", default=False)

    class Meta:
        unique_together = ('bk_app_code', 'env')

    def __str__(self):
        return f"{self.bk_app_code}_{self.env}[{self.data_token}]"
