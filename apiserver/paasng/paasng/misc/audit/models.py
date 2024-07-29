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
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from paasng.infras.iam.constants import ResourceType
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import AccessType, DataType, OperationEnum, OperationTarget, ResultCode
from paasng.platform.applications.models import Application
from paasng.platform.engine.constants import AppEnvName
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.models import AuditedModel, BkUserField


class BaseOperation(AuditedModel):
    # 保留自增的 ID 作为主键，方便通过 Max(id) 获取每个应用最近一条操作记录
    event_id = models.UUIDField(verbose_name="事件ID", default=uuid.uuid4, help_text="用于上报到审计中心的字段")
    user = BkUserField()
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")
    end_time = models.DateTimeField(null=True, help_text="仅需要后台执行的的操作才需要记录结束时间")
    access_type = models.IntegerField(
        verbose_name="访问方式", choices=AccessType.get_choices(), default=AccessType.WEB
    )
    result_code = models.IntegerField(
        verbose_name="操作结果", choices=ResultCode.get_choices(), default=ResultCode.SUCCESS
    )
    data_type = models.CharField(
        max_length=32,
        verbose_name="操作的数据类型",
        choices=DataType.get_choices(),
        default=DataType.NO_DATA,
        help_text="该字段决定了 data_before、data_after 记录的数据类型，以及前端展示的样式",
    )
    data_before = models.TextField(verbose_name="操作前的数据", null=True, blank=True)
    data_after = models.TextField(verbose_name="操作后的数据", null=True, blank=True)

    operation = models.CharField(max_length=32, verbose_name="操作类型", choices=OperationEnum.get_choices())
    target = models.CharField(max_length=32, verbose_name="操作对象", choices=OperationTarget.get_choices())
    attribute = models.CharField(
        max_length=32,
        verbose_name="对象属性",
        help_text="如增强服务的属性可以为：mysql、bkrepo",
        null=True,
        blank=True,
    )

    # 只记录 module_name，保证 module 删除时相关记录仍旧存在
    module_name = models.CharField(max_length=32, verbose_name="模块名，非必填", null=True, blank=True)
    env = models.CharField(
        max_length=16, verbose_name="环境，非必填", choices=AppEnvName.get_choices(), null=True, blank=True
    )

    class Meta:
        abstract = True

    @property
    def username(self):
        return get_username_by_bkpaas_user_id(self.user)

    @property
    def scope_type(self):
        """审计中心的冗余字段，用于细化接入权限中心的 action"""
        return self.target

    @property
    def scope_id(self):
        """审计中心的冗余字段，用于细化接入权限中心的 action"""
        return f"{self.operation}|{self.attribute}|{self.module_name}|{self.env}"

    @property
    def result_display(self):
        if self.result_code in ResultCode.terminated_result():
            return self.get_result_code_display()
        return ""

    def get_display_text(self):
        """操作记录描述，用于首页、应用概览页面前 5 条部署记录的展示"""
        env = self.get_env_display()
        if self.module_name and env:
            module_env_info = _(f" {self.module_name} 模块{env}")
        elif self.module_name:
            module_env_info = _(f" {self.module_name} 模块")
        elif self.env:
            module_env_info = _(f"{env}")
        else:
            module_env_info = ""

        ctx = {
            "user": self.username,
            "operation": self.get_operation_display(),
            "target": self.get_target_display(),
            "attribute": self.attribute,
            "module_env_info": module_env_info,
            "result": self.result_display,
        }
        if self.attribute:
            # admin 启用 default 模块预发布环境 mysql 增强服务成功
            # admin 申请 bklog 网关云API权限
            return _("{user} {operation}{module_env_info} {attribute} {target}{result}").format(**ctx)

        if self.target == OperationTarget.APP:
            # target 为应用时不展示，如：admin 部署 default 模块预发布环境成功
            return _("{user} {operation}{module_env_info}{result}").format(**ctx)

        # admin 修改 default 模块环境变量成功
        return _("{user} {operation}{module_env_info}{target}{result}").format(**ctx)


class AdminOperationRecord(BaseOperation):
    """后台管理操作记录，用于记录平台管理员在 Admin 系统上的操作"""

    app_code = models.CharField(max_length=32, verbose_name="应用ID, 非必填", null=True, blank=True)


class AppAuditRecord(BaseOperation):
    """应用操作审计，用于记录应用开发者的操作，需要同步记录应用的权限数据，并可以选择是否将数据上报到审计中心"""

    # 后续可能会做应用的硬删除，记录应用 ID，方便应用删除后相关记录仍存在
    app_code = models.CharField(max_length=32, verbose_name="应用ID, 必填")
    source_object_id = models.CharField(
        default="", null=True, blank=True, max_length=32, help_text="事件来源对象ID,用于异步事件更新操作记录状态"
    )

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

    @property
    def application(self):
        try:
            app = Application.default_objects.get(code=self.app_code)
        except ObjectDoesNotExist:
            return None
        return app
