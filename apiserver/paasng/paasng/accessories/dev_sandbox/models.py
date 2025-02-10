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

import string
from datetime import timedelta

from blue_krill.models.fields import EncryptField
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from paas_wl.bk_app.dev_sandbox.constants import DevSandboxStatus
from paas_wl.utils.models import make_json_field
from paasng.accessories.dev_sandbox.utils import generate_password
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.models import VersionInfo
from paasng.utils.models import OwnerTimestampedModel, UuidAuditedModel

VersionInfoField = make_json_field("VersionInfoField", VersionInfo)

DEV_SANDBOX_CODE_CHARSETS = string.ascii_lowercase + string.digits


class DevSandboxQuerySet(models.QuerySet):
    """开发沙箱 QuerySet 类"""

    def create(self, module: Module, version_info: VersionInfo, owner: str) -> "DevSandbox":
        # 生成唯一的沙箱标识
        while True:
            code = get_random_string(8, DEV_SANDBOX_CODE_CHARSETS)
            if not super().filter(code=code).exists():
                break

        return super().create(
            code=code,
            module=module,
            owner=owner,
            status=DevSandboxStatus.ACTIVE,
            expired_at=timezone.now() + timedelta(hours=2),
            version_info=version_info,
            token=generate_password(),
            tenant_id=module.tenant_id,
        )


DevSandboxManager = models.Manager.from_queryset(DevSandboxQuerySet)


class DevSandbox(OwnerTimestampedModel):
    """开发沙箱"""

    code = models.CharField(max_length=8, help_text="沙箱标识", unique=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, db_constraint=False)
    # 枚举值参见：DevSandboxStatus
    status = models.CharField(max_length=32, verbose_name="沙箱状态")
    expired_at = models.DateTimeField(null=True, help_text="到期时间")
    version_info = VersionInfoField(help_text="代码版本信息", default=None, null=True)
    token = EncryptField(help_text="访问令牌", null=True)
    tenant_id = tenant_id_field_factory()

    objects = DevSandboxManager()

    def renew_expired_at(self):
        self.expired_at = timezone.now() + timedelta(hours=2)
        self.save(update_fields=["expired_at", "updated"])

    class Meta:
        unique_together = ("module", "owner")


class CodeEditorQuerySet(models.QuerySet):
    """代码编辑器 QuerySet 类"""

    def create(self, dev_sandbox: "DevSandbox") -> "CodeEditor":
        return super().create(
            dev_sandbox=dev_sandbox,
            password=generate_password(),
            tenant_id=dev_sandbox.tenant_id,
        )


CodeEditorManager = models.Manager.from_queryset(CodeEditorQuerySet)


class CodeEditor(UuidAuditedModel):
    """代码编辑器"""

    dev_sandbox = models.OneToOneField(
        DevSandbox,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="code_editor",
    )
    password = EncryptField(help_text="登录密码")
    tenant_id = tenant_id_field_factory()

    objects = CodeEditorManager()
