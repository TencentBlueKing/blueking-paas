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

import logging
from collections import namedtuple
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Optional

from django.db import models
from django.utils.translation import gettext_lazy as _
from jsonfield import JSONField

from paas_wl.bk_app.cnative.specs.models import AppModelDeploy
from paasng.misc.operations.constant import OperationType as OpType
from paasng.platform.applications.models import Application
from paasng.platform.engine.constants import AppEnvName, JobStatus
from paasng.platform.engine.models import Deployment
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.models import BkUserField

if TYPE_CHECKING:
    from paasng.platform.engine.models.offline import OfflineOperation

logger = logging.getLogger(__name__)


class Operation(models.Model):
    region = models.CharField(max_length=32, help_text="部署区域")
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    user = BkUserField()
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, help_text="操作的PAAS应用", null=True, blank=True
    )
    type = models.SmallIntegerField(help_text="操作类型", db_index=True)
    is_hidden = models.BooleanField(default=False, help_text="隐藏起来")  # 同一事件最终只展示一条记录
    source_object_id = models.CharField(
        default="", null=True, blank=True, max_length=32, help_text="事件来源对象ID，具体指向需要根据操作类型解析"
    )
    # 只记录 module_name，保证 module 删除时相关记录仍旧存在
    module_name = models.CharField(null=True, verbose_name="关联 Module", max_length=20)
    extra_values = JSONField(default={}, help_text="操作额外信息", blank=True)

    def get_operator(self):
        # 之前记录的有漏洞
        if not self.user:
            return ""
        return get_username_by_bkpaas_user_id(self.user)

    def get_operate_display(self):
        return get_operation_obj(self).get_text_display()


class ApplicationLatestOp(models.Model):
    """A mapper table which saves application's latest operation"""

    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, db_constraint=False, related_name="latest_op"
    )
    operation_type = models.SmallIntegerField(help_text="操作类型")
    operation = models.OneToOneField(Operation, on_delete=models.CASCADE, db_constraint=False)
    latest_operated_at = models.DateTimeField(db_index=True)


# Wrapper class for Operation


class OperationObj:
    """Common operation object"""

    def __init__(self, operation: Operation):
        self.operation = operation
        self.op_type = OpType(self.operation.type)

    def get_text_display(self):
        for value, text in OpType.get_choices():
            if value == self.op_type.value:
                return _(text)
        return None


class UnknownTypeOperationObj(OperationObj):
    def __init__(self, operation: Operation):
        self.operation = operation

    def get_text_display(self):
        return _("未知操作类型")


class ProcessOperationObj(OperationObj):
    """Operation object: processs start/stop"""

    _text_tmpls = {
        OpType.PROCESS_START: _("启动 {module_name} 模块的 {process_type} 进程"),
        OpType.PROCESS_STOP: _("停止 {module_name} 模块的 {process_type} 进程"),
    }

    def get_text_display(self):
        process_type = self.operation.extra_values.get("process_type", _("未知"))
        return self._text_tmpls[self.op_type].format(module_name=self.operation.module_name, process_type=process_type)


@dataclass
class DeployOpValues:
    env_name: str
    has_succeeded: bool
    # `status` is optional to be compatible with legacy database data
    status: Optional[str] = None


class AppDeploymentOperationObj(OperationObj):
    """Operation object: app deployment"""

    default_op_type = OpType.DEPLOY_APPLICATION
    values_type = DeployOpValues

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.extra_values = self.values_type(**self.operation.extra_values)
        except TypeError:
            self.extra_values = self.values_type(env_name="", has_succeeded=False)

    @classmethod
    def create_from_deployment(cls, deployment: Deployment):
        """Construct an operation object by deployment"""
        application = deployment.app_environment.application
        operation = Operation(
            type=cls.default_op_type.value,
            application=application,
            user=deployment.operator,
            source_object_id=deployment.id.hex,
            module_name=deployment.app_environment.module.name,
            extra_values=asdict(
                cls.values_type(
                    env_name=deployment.app_environment.environment,
                    has_succeeded=deployment.has_succeeded(),
                    status=deployment.status,
                )
            ),
        )
        operation.save()
        return operation

    def get_text_display(self) -> str:
        if self.extra_values.status is not None:
            status = JobStatus(self.extra_values.status)
        else:
            # Backward compatible with data which don't have `status` field
            status = JobStatus.SUCCESSFUL if self.extra_values.has_succeeded else JobStatus.FAILED

        text_tmpl = self.get_tmpl_from_status(status)
        env_name = AppEnvName.get_choice_label(self.extra_values.env_name) or _("未知")
        return text_tmpl.format(module_name=self.operation.module_name, env_name=env_name)

    @staticmethod
    def get_tmpl_from_status(status: JobStatus):
        if status == JobStatus.SUCCESSFUL:
            return _("成功部署 {module_name} 模块的{env_name}")
        elif status == JobStatus.INTERRUPTED:
            return _("中断了 {module_name} 模块的{env_name}的部署过程")
        else:
            return _("尝试部署 {module_name} 模块的{env_name}失败")


class CNativeAppDeployOperationObj(OperationObj):
    """Operation object: paas_wl.bk_app.cnative.specs.models.AppModelDeploy"""

    default_op_type = OpType.DEPLOY_CNATIVE_APP
    values_type = DeployOpValues

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.extra_values = self.values_type(**self.operation.extra_values)
        except TypeError:
            self.extra_values = self.values_type(env_name="", has_succeeded=False)

    @classmethod
    def create_from_deploy(cls, deploy: AppModelDeploy):
        """Construct an operation object by deployment"""
        application = Application.objects.get(id=deploy.application_id)
        operation = Operation(
            region=deploy.region,
            type=cls.default_op_type.value,
            application=application,
            user=deploy.operator,
            source_object_id=deploy.pk,
            module_name=deploy.module.name,
            extra_values=asdict(
                cls.values_type(
                    env_name=deploy.environment_name,
                    has_succeeded=deploy.has_succeeded(),
                    status=deploy.status,
                )
            ),
        )
        operation.save()
        return operation

    def get_text_display(self) -> str:
        text_tmpl = (
            _("成功部署 {module_name} 模块的{env_name}")
            if self.extra_values.has_succeeded
            else _("尝试部署 {module_name} 模块的{env_name}失败")
        )
        env_name = AppEnvName.get_choice_label(self.extra_values.env_name) or _("未知")
        return text_tmpl.format(module_name=self.operation.module_name, env_name=env_name)


class AppOfflineOperationObj(OperationObj):
    values_type = namedtuple("values_type", "env_name has_succeeded")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.extra_values = self.values_type(**self.operation.extra_values)
        except TypeError:
            self.extra_values = self.values_type(has_succeeded=False, env_name="")

    @classmethod
    def get_operation_type(cls, offline_instance: "OfflineOperation"):
        if offline_instance.app_environment.environment == "stag":
            return OpType.OFFLINE_APPLICATION_STAG_ENVIRONMENT
        elif offline_instance.app_environment.environment == "prod":
            return OpType.OFFLINE_APPLICATION_PROD_ENVIRONMENT
        return None

    @classmethod
    def assemble_operation_params(cls, offline_instance: "OfflineOperation") -> dict:
        application = offline_instance.app_environment.application
        module_name = offline_instance.app_environment.module.name

        return dict(
            application=application,
            type=cls.get_operation_type(offline_instance).value,
            user=offline_instance.operator,
            region=application.region,
            source_object_id=offline_instance.id.hex,
            module_name=module_name,
        )

    @classmethod
    def update_operation(cls, offline_instance: "OfflineOperation"):
        o = Operation.objects.get(**cls.assemble_operation_params(offline_instance))
        o.extra_values = dict(
            has_succeeded=offline_instance.has_succeeded(), env_name=offline_instance.app_environment.environment
        )
        o.save(update_fields=["extra_values"])

    @classmethod
    def create_operation(cls, offline_instance: "OfflineOperation"):
        Operation.objects.create(**cls.assemble_operation_params(offline_instance))

    def get_text_display(self):
        env_name = AppEnvName.get_choice_label(self.extra_values.env_name) or _("未知")
        if not env_name:
            return super().get_text_display()

        if self.extra_values.has_succeeded:
            text_tmpl = _("成功下架 {module_name} 模块的{env_name}")
        else:
            text_tmpl = _("尝试下架 {module_name} 模块的{env_name}")

        return text_tmpl.format(module_name=self.operation.module_name, env_name=env_name)


class CreateModuleOperationObj(OperationObj):
    """Operation object: create a new module"""

    def get_text_display(self):
        return _("创建 {module_name} 模块").format(module_name=self.operation.module_name)


class ApplyCloudApiOperationObj(OperationObj):
    """Operation object: apply for or renew ApiGateway API permissions"""

    _text_tmpls = {
        OpType.APPLY_PERM_FOR_CLOUD_API: _("申请 {gateway_name} 网关的 API 权限"),
        OpType.RENEW_PERM_FOR_CLOUD_API: _("续期 {gateway_name} 网关的 API 权限"),
    }

    def get_text_display(self):
        gateway_name = self.operation.extra_values.get("gateway_name", "")
        return self._text_tmpls[self.op_type].format(gateway_name=gateway_name)


_operation_cls_map = {
    OpType.DEPLOY_APPLICATION: AppDeploymentOperationObj,
    OpType.DEPLOY_CNATIVE_APP: CNativeAppDeployOperationObj,
    OpType.PROCESS_START: ProcessOperationObj,
    OpType.PROCESS_STOP: ProcessOperationObj,
    OpType.CREATE_MODULE: CreateModuleOperationObj,
    OpType.OFFLINE_APPLICATION_STAG_ENVIRONMENT: AppOfflineOperationObj,
    OpType.OFFLINE_APPLICATION_PROD_ENVIRONMENT: AppOfflineOperationObj,
}


def get_operation_obj(operation: Operation) -> OperationObj:
    """Return an operation object by operation db object"""
    try:
        op_type = OpType(operation.type)
    except ValueError:
        return UnknownTypeOperationObj(operation)

    cls = _operation_cls_map.get(op_type, OperationObj)
    return cls(operation)
