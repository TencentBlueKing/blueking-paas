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

from paasng.infras.iam.helpers import delete_builtin_user_groups, delete_grade_manager
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import add_app_audit_record
from paasng.platform.applications.models import Application
from paasng.platform.modules.manager import ModuleCleaner

logger = logging.getLogger(__name__)


class ApplicationCleaner:
    def __init__(self, application: Application):
        self.application = application

    def clean(self):
        """main entrance to clean application"""
        logger.info("going to delete iam resources for Application<%s>", self.application)
        self.delete_iam_resources()

        # 软删除, 标记 is_deleted = True
        logger.info("going to delete Application<%s>", self.application)
        self.delete_application()

    def delete_iam_resources(self):
        """删除 IAM 相关资源"""
        # 删除应用的内建用户组
        logger.info("delete all builtin user groups for application(%s)", self.application)
        delete_builtin_user_groups(app_code=self.application.code)

        # 删除应用的分级管理员
        logger.info("delete grade manager for application(%s)", self.application)
        delete_grade_manager(app_code=self.application.code)

    def delete_application(self):
        """删除应用的数据库记录(软删除)"""
        # 不会删除数据, 而是通过标记删除字段 is_deleted 来软删除
        self.application.delete()


def delete_all_modules(application: Application, operator: str):
    """删除应用下的所有 Module"""
    modules = application.modules.all()
    for module in modules:
        ModuleCleaner(module).clean()
        # 审计记录
        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=operator,
            action_id=AppAction.MANAGE_MODULE,
            operation=OperationEnum.DELETE,
            target=OperationTarget.MODULE,
        )
