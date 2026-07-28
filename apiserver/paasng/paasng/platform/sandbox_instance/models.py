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

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.agent_sandbox.models import ImageBuildRecord
from paasng.utils.models import UuidAuditedModel


class SidecarImage(UuidAuditedModel):
    """可用的 Sidecar 容器镜像记录。

    由两种方式产生：
    1. 通过构建流程（Kaniko）构建成功后自动注册
    2. 通过 register 接口直接注册已有镜像地址
    """

    app_code = models.CharField(max_length=20, help_text="发起方应用 code（sysapi client）")
    image = models.CharField(max_length=512, help_text="完整镜像地址（registry/namespace/name:tag）")
    name = models.CharField(max_length=256, help_text="镜像名称（用于展示/筛选）")
    tag = models.CharField(max_length=128, help_text="镜像标签")
    build_record = models.ForeignKey(
        ImageBuildRecord,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False,
        related_name="sidecar_images",
        help_text="关联的构建记录（直接注册时为空）",
    )
    tenant_id = tenant_id_field_factory()

    class Meta:
        ordering = ["-created"]
        unique_together = ("tenant_id", "app_code", "image")

    def __str__(self):
        return f"{self.app_code}/{self.name}:{self.tag}"
