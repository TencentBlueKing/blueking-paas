# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

from paas_wl.bk_app.applications.models import UuidAuditedModel


class OutputStream(UuidAuditedModel):
    """
    [multi-tenancy] TODO
    """

    def write(self, line, stream="STDOUT"):
        if not line.endswith("\n"):
            line += "\n"
        OutputStreamLine.objects.create(output_stream=self, line=line, stream=stream)


class OutputStreamLine(models.Model):
    """
    [multi-tenancy] TODO
    """

    output_stream = models.ForeignKey("OutputStream", related_name="lines", on_delete=models.CASCADE)
    stream = models.CharField(max_length=16)
    line = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created"]

    def __str__(self):
        return "%s-%s" % (self.id, self.line)
