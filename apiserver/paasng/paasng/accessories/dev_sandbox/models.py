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
import json
import string
from datetime import timedelta

from blue_krill.models.fields import EncryptField
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig
from paasng.accessories.dev_sandbox.utils import generate_password
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.models import VersionInfo
from paasng.utils.models import OwnerTimestampedModel, make_json_field

VersionInfoField = make_json_field("VersionInfoField", VersionInfo)

CodeEditorConfigField = make_json_field("CodeEditorConfigField", CodeEditorConfig)

# 默认 2h 无活动后会回收沙箱
DEV_SANDBOX_DEFAULT_EXPIRED_DURATION = timedelta(hours=2)


class DevSandboxQuerySet(models.QuerySet):
    """
    开发沙箱 QuerySet 类

    Q：为什么是在 QuerySet 中定义 create 方法，而不是在 Manager 中定义？
    A：查阅 Django 源码可发现，Manager 中的 filter，create 等方法其实是继承自 QuerySet 类的，
      如果只覆写 Manager 中的 create 方法，则在 DevSandbox.objects.get_or_create() 时，
      实际会被调用到的是没有被覆写的 QuerySet.create() 方法，并非预期的 create() 方法。
    """

    def create(
        self,
        module: Module,
        owner: str,
        version_info: VersionInfo | None,
        enable_code_editor: bool = False,
        env_vars: list | None = None,
    ) -> "DevSandbox":
        charsets = string.ascii_lowercase + string.digits

        # 最大重试次数
        max_retries, retry_count = 10, 0
        # 生成唯一的沙箱标识
        while retry_count < max_retries:
            # 生成唯一的沙箱标识
            code = get_random_string(8, charsets)
            if not super().filter(code=code).exists():
                break
            retry_count += 1
        else:
            # 达到最大重试次数，抛出异常
            raise ValueError("Failed to generate a unique dev sandbox code after maximum retries.")

        code_editor_cfg: CodeEditorConfig | None = None
        if enable_code_editor:
            code_editor_cfg = CodeEditorConfig(password=generate_password())

        if env_vars is None:
            env_vars_json = None
        else:
            env_vars_json = json.dumps(env_vars)

        return super().create(
            code=code,
            module=module,
            owner=owner,
            expired_at=timezone.now() + DEV_SANDBOX_DEFAULT_EXPIRED_DURATION,
            version_info=version_info,
            token=generate_password(),
            code_editor_config=code_editor_cfg,
            tenant_id=module.tenant_id,
            env_vars=env_vars_json,
        )


DevSandboxManager = models.Manager.from_queryset(DevSandboxQuerySet)


class DevSandbox(OwnerTimestampedModel):
    """开发沙箱"""

    code = models.CharField(max_length=8, help_text="沙箱标识", unique=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, db_constraint=False)
    expired_at = models.DateTimeField(null=True, help_text="到期时间")
    version_info = VersionInfoField(help_text="代码版本信息", default=None, null=True)
    token = EncryptField(help_text="访问令牌", null=True)
    code_editor_config = CodeEditorConfigField(help_text="代码编辑器配置", default=None, null=True)
    tenant_id = tenant_id_field_factory()
    env_vars = EncryptField(help_text="沙箱环境变量", default=list, null=True, blank=True)

    objects = DevSandboxManager()

    def renew_expired_at(self):
        """由周期任务定时调用，刷新过期时间"""
        self.expired_at = timezone.now() + DEV_SANDBOX_DEFAULT_EXPIRED_DURATION
        self.save(update_fields=["expired_at", "updated"])

    def retrieve_env_vars(self) -> list:
        """获取沙箱环境变量"""
        if not self.env_vars:
            return []

        return json.loads(self.env_vars)

    def set_env_vars(self, new_env_vars: list | None):
        """设置沙箱环境变量"""
        if new_env_vars is None:
            setattr(self, "env_vars", None)
        else:
            validated_vars = []
            for item in new_env_vars:
                if "source" not in item:
                    item["source"] = "custom"
                validated_vars.append(item)

            setattr(self, "env_vars", json.dumps(validated_vars))

    def update_env_vars(self, new_vars: list | None):
        """更新环境变量"""
        if new_vars is None:
            return

        current_envs = self.retrieve_env_vars()
        current_dict = {item["key"]: item for item in current_envs}

        # 更新或添加新变量
        for new_item in new_vars:
            key = new_item["key"]

            if "source" not in new_item:
                new_item["source"] = "custom"

            current_dict[key] = new_item

        updated_list = list(current_dict.values())
        self.set_env_vars(updated_list)

    class Meta:
        unique_together = ("module", "owner")
