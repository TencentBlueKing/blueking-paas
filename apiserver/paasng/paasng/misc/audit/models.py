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
from typing import Optional

from django.db import models
from django.utils.translation import gettext_lazy as _

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.infras.iam.constants import ResourceType
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import AccessType, OperationEnum, OperationTarget, ResultCode
from paasng.platform.applications.models import Application
from paasng.platform.engine.constants import AppEnvName
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.models import BkUserField, UuidAuditedModel


class BaseOperation(UuidAuditedModel):
    user = BkUserField()
    # 时间字段手添加索引，方便审计记录表过大时做分区优化
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="开始时间", db_index=True)
    end_time = models.DateTimeField(null=True, help_text="仅需要后台执行的的操作才需要记录结束时间")
    access_type = models.IntegerField(
        verbose_name="访问方式", choices=AccessType.get_choices(), default=AccessType.WEB
    )
    result_code = models.IntegerField(
        verbose_name="操作结果", choices=ResultCode.get_choices(), default=ResultCode.SUCCESS
    )
    data_before = models.JSONField(verbose_name="操作前的数据", null=True, blank=True)
    data_after = models.JSONField(verbose_name="操作后的数据", null=True, blank=True)

    # 可选枚举值：OperationEnum
    operation = models.CharField(max_length=32, verbose_name="操作类型")
    # 可选枚举值：OperationTarget
    target = models.CharField(max_length=32, verbose_name="操作对象")
    attribute = models.CharField(
        max_length=128,
        verbose_name="对象属性",
        help_text="如增强服务的属性可以为：mysql、bkrepo",
        null=True,
        blank=True,
    )

    # 只记录 module_name，保证 module 删除时相关记录仍旧存在
    module_name = models.CharField(max_length=32, verbose_name="模块名，非必填", null=True, blank=True)
    environment = models.CharField(
        max_length=16, verbose_name="环境，非必填", choices=AppEnvName.get_choices(), null=True, blank=True
    )

    class Meta:
        abstract = True

    @property
    def username(self) -> str:
        if self.user:
            return get_username_by_bkpaas_user_id(self.user)
        return ""

    @property
    def scope_type(self) -> str:
        """审计中心的冗余字段，用于细化接入权限中心的 action"""
        return self.target

    @property
    def scope_id(self) -> str:
        """审计中心的冗余字段，用于细化接入权限中心的 action"""
        return f"{self.operation}|{self.attribute}|{self.module_name}|{self.environment}"

    @property
    def is_terminated(self) -> bool:
        return self.result_code in ResultCode.get_terminated_codes()

    @property
    def result_display(self) -> str:
        if self.is_terminated:
            return self.get_result_code_display()
        # 不是终止状态，则不再描述的信息中展示
        # 如 admin 启动 web 进程成功；admin 启动 web 进程
        return ""

    @property
    def need_to_report_bk_audit(self) -> bool:
        # 仅操作为终止状态时才记录到审计中心
        return self.action_id and self.is_terminated

    def get_display_text(self) -> str:
        """操作记录描述，用于首页、应用概览页面前 5 条部署记录的展示"""
        env = self.get_environment_display()
        if self.module_name and self.environment:
            module_env_info = _(" {module_name} 模块{env}").format(module_name=self.module_name, env=env)
        elif self.module_name:
            module_env_info = _(" {module_name} 模块").format(module_name=self.module_name)
        elif self.environment:
            module_env_info = _("{env}").format(env=env)
        else:
            module_env_info = ""

        ctx = {
            "user": self.username,
            "operation": OperationEnum.get_choice_label(self.operation),
            "target": OperationTarget.get_choice_label(self.target),
            "attribute": self.attribute,
            "module_env_info": module_env_info,
            "result": self.result_display,
        }

        if self.target == OperationTarget.APP:
            # target 为应用时不展示，如：admin 部署 default 模块预发布环境成功
            return _("{user} {operation}{module_env_info}{result}").format(**ctx)

        if self.attribute:
            if self.target == OperationTarget.CLOUD_API:
                # admin 申请 bklog 网关云API权限
                return _("{user} {operation}{module_env_info} {attribute} 网关 API 权限").format(**ctx)
            # admin 启用 default 模块预发布环境 mysql 增强服务成功
            return _("{user} {operation}{module_env_info} {attribute} {target}{result}").format(**ctx)

        # admin 修改 default 模块环境变量成功
        return _("{user} {operation}{module_env_info}{target}{result}").format(**ctx)


class AdminOperationRecord(BaseOperation):
    """后台管理操作记录，用于记录平台管理员在 Admin 系统上的操作

    [multi-tenancy] This model is not tenant-aware.
    """

    app_code = models.CharField(max_length=32, verbose_name="应用ID, 非必填", null=True, blank=True)


class AppOperationRecord(BaseOperation):
    """应用操作记录，用于记录应用开发者的操作，需要同步记录应用的权限数据，并可以选择是否将数据上报到审计中心"""

    # 后续可能会做应用的硬删除，记录应用 ID，方便应用删除后相关记录仍存在
    app_code = models.CharField(max_length=32, verbose_name="应用ID, 必填")

    # 注册到权限中心的字段，字段的值需要跟注册到权限中心的值保持一致
    action_id = models.CharField(
        max_length=32,
        choices=AppAction.get_choices(),
        null=True,
        blank=True,
        help_text="action_id 为空则不会将数据上报到审计中心",
    )
    resource_type_id = models.CharField(
        max_length=32,
        choices=ResourceType.get_choices(),
        default=ResourceType.Application,
        help_text="开发者中心注册的资源都为蓝鲸应用",
    )

    tenant_id = tenant_id_field_factory()

    @property
    def application(self) -> Optional[Application]:
        return Application.default_objects.filter(code=self.app_code).first()


class AppLatestOperationRecord(models.Model):
    """应用最近操作的映射表，可方便快速查询应用的最近操作者，并按最近操作时间进行排序等操作
    当 `AppOperationRecord` 新增记录时，会通过 signal 同步添加到该表中
    """

    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, db_constraint=False, related_name="latest_op_record"
    )
    operation = models.OneToOneField(AppOperationRecord, on_delete=models.CASCADE, db_constraint=False)
    latest_operated_at = models.DateTimeField(db_index=True)

    tenant_id = tenant_id_field_factory()
