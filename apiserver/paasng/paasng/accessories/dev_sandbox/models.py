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

from blue_krill.models.fields import EncryptField
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from paas_wl.bk_app.dev_sandbox.constants import DevSandboxStatus
from paas_wl.utils.models import make_json_field
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.models import VersionInfo
from paasng.utils.models import OwnerTimestampedModel, UuidAuditedModel

VersionInfoField = make_json_field("VersionInfoField", VersionInfo)


def gen_dev_sandbox_code() -> str:
    """生成随机的唯一的沙箱标识(只包含小写字母和数字)"""
    characters = string.ascii_lowercase + string.digits
    dev_sandbox_code = get_random_string(8, characters)
    while DevSandbox.objects.filter(code=dev_sandbox_code).exists():
        dev_sandbox_code = get_random_string(8, characters)
    return dev_sandbox_code


class DevSandbox(OwnerTimestampedModel):
    """DevSandbox Model"""

    code = models.CharField(max_length=8, help_text="沙箱标识", unique=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, db_constraint=False)
    status = models.CharField(max_length=32, verbose_name="沙箱状态", choices=DevSandboxStatus.get_choices())
    expired_at = models.DateTimeField(null=True, help_text="到期时间")
    version_info = VersionInfoField(help_text="代码版本信息", default=None, null=True)

    def renew_expired_at(self):
        self.expired_at = timezone.now() + timezone.timedelta(hours=2)
        self.save(update_fields=["expired_at"])

    class Meta:
        unique_together = ("module", "owner")


class CodeEditor(UuidAuditedModel):
    """CodeEditor Model"""

    dev_sandbox = models.OneToOneField(
        DevSandbox, on_delete=models.CASCADE, db_constraint=False, related_name="code_editor"
    )
    password = EncryptField(max_length=32, verbose_name="登录密码", help_text="登录密码")
