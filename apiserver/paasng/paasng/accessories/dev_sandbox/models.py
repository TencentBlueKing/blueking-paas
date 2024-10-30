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
import datetime
import random
import string

from blue_krill.models.fields import EncryptField
from django.db import models

from paas_wl.bk_app.dev_sandbox.constants import DevSandboxStatus
from paas_wl.utils.models import make_json_field
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.models import VersionInfo
from paasng.utils.models import OwnerTimestampedModel, UuidAuditedModel

VersionInfoField = make_json_field("VersionInfoField", VersionInfo)


def generate_random_code(length: int = 8) -> str:
    """生成随机的沙箱标识(只包含小写字母和数字)"""
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def gen_dev_sandbox_code() -> str:
    """生成随机的唯一的沙箱标识"""
    dev_sandbox_code = generate_random_code()
    while DevSandbox.objects.filter(code=dev_sandbox_code).exists():
        dev_sandbox_code = generate_random_code()
    return dev_sandbox_code


class DevSandbox(OwnerTimestampedModel):
    """DevSandbox Model"""

    code = models.CharField(max_length=8, help_text="沙箱标识", unique=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, db_constraint=False)
    status = models.CharField(max_length=32, verbose_name="沙箱状态", choices=DevSandboxStatus.get_choices())
    expire_at = models.DateTimeField(null=True, help_text="到期时间")
    version_info = VersionInfoField(help_text="代码版本信息", default=None, null=True)

    def renew_expire_at(self):
        # 如果状态不是ALIVE, 则设置两小时后过期
        if self.status != DevSandboxStatus.ACTIVE.value:
            self.expire_at = datetime.datetime.now() + datetime.timedelta(hours=2)
        else:
            self.expire_at = None
        self.save(update_fields=["expire_at"])

    def should_recycle(self) -> bool:
        """检查是否应该被回收"""
        if self.expire_at:
            return self.expire_at <= datetime.datetime.now()
        return False

    class Meta:
        unique_together = ("module", "owner")


class CodeEditor(UuidAuditedModel):
    """CodeEditor Model"""

    dev_sandbox = models.OneToOneField(
        DevSandbox, on_delete=models.CASCADE, db_constraint=False, related_name="code_editor"
    )
    password = EncryptField(max_length=32, verbose_name="登陆密码", help_text="登陆密码")
