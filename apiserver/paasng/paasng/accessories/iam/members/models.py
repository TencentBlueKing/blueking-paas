# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
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
import logging

from django.db import models

from paasng.platform.applications.constants import ApplicationRole
from paasng.utils.models import AuditedModel

logger = logging.getLogger(__name__)


class ApplicationGradeManager(AuditedModel):
    """
    IAM 分级管理员与开发者中心应用的关系

    分级管理员管理用户加入用户组的申请，理论上来说，某个应用的分级管理员与管理者的成员是一致的
    """

    app_code = models.CharField(max_length=20, help_text='应用代号')
    grade_manager_id = models.IntegerField(help_text='分级管理员 ID')

    class Meta:
        unique_together = ('app_code', 'grade_manager_id')

    def __str__(self):
        return "{app_code}-{grade_manager_id}".format(app_code=self.app_code, grade_manager_id=self.grade_manager_id)


class ApplicationUserGroup(AuditedModel):
    """
    IAM 用户组与开发者中心应用的关系

    每个应用默认会有 3 个用户组（不可删除）：管理者，开发者，运营者
    """

    app_code = models.CharField(max_length=20, help_text='应用代号')
    role = models.IntegerField(default=ApplicationRole.DEVELOPER.value)
    user_group_id = models.IntegerField(help_text='权限中心用户组 ID')

    class Meta:
        unique_together = ('app_code', 'role')

    def __str__(self):
        return "{app_code}-{role}-{user_group_id}".format(
            app_code=self.app_code, role=ApplicationRole.get_choice_label(self.role), user_group_id=self.user_group_id
        )
