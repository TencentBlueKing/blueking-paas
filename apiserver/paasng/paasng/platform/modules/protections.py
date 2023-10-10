# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
"""Preconditions for publish Application/Module"""
from django.utils.translation import gettext as _

from paas_wl.workloads.networking.entrance.shim import LiveEnvAddresses
from paasng.platform.engine.models.managers import DeployOperationManager
from paasng.platform.engine.utils.query import DeploymentGetter, OfflineOperationGetter
from paasng.core.core.protections.base import BaseCondition, BaseConditionChecker
from paasng.core.core.protections.exceptions import ConditionNotMatched
from paasng.platform.modules.models import Module


class ModuleDeleteCondition(BaseCondition):
    """Abstract base class for delete module condition"""

    def __init__(self, module: Module):
        self.module = module

    def validate(self):
        raise NotImplementedError


class NoPendingOperationsCondition(ModuleDeleteCondition):
    """检查模块是否存在未完成的操作(部署或下架)"""

    action_name = 'wait_operation_finish'

    def validate(self):
        if DeployOperationManager(self.module).has_pending():
            raise ConditionNotMatched(
                _("{module_name} 模块正在进行部署或下架操作，请操作结束后再尝试删除").format(module_name=self.module.name),
                action_name=self.action_name,
            )


class AllEnvsArchivedCondition(ModuleDeleteCondition):
    """检查模块的所有环境是否均已下架"""

    action_name = "archive_env"

    def validate(self):
        # 删除模块时, 需要用户主动下架所有环境, 已保证模块删除成功.
        for env in self.module.get_envs():
            if DeploymentGetter(env).get_latest_succeeded() is None:
                continue

            if OfflineOperationGetter(env).get_latest_succeeded() is None:
                # 存在某个环境没有完全下架
                raise ConditionNotMatched(
                    _("删除模块前，请先将所有部署环境下架"),
                    action_name=self.action_name,
                )


class CustomDomainUnBoundCondition(ModuleDeleteCondition):
    """检查模块是否已解绑所有独立域名"""

    action_name = "unbind_custom_domain"

    def validate(self):
        for env in self.module.get_envs():
            if LiveEnvAddresses(env).list_custom():
                raise ConditionNotMatched(_("删除模块前，请先确认所有独立域名已经下线"), action_name=self.action_name)


class ModuleDeletionPreparer(BaseConditionChecker):
    """Prepare to delete a module"""

    condition_classes = [NoPendingOperationsCondition, AllEnvsArchivedCondition, CustomDomainUnBoundCondition]

    def __init__(self, module: Module):
        self.module = module
        self.conditions = [cls(module) for cls in self.condition_classes]
