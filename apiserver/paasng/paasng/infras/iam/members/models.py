# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from django.db import models

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.applications.constants import ApplicationRole
from paasng.utils.models import AuditedModel

logger = logging.getLogger(__name__)


class ApplicationGradeManager(AuditedModel):
    """
    IAM 分级管理员（V4 语义为管理空间）与开发者中心应用的关系

    分级管理员管理用户加入用户组的申请，理论上来说，某个应用的分级管理员与管理者的成员是一致的

    note: 每个部署环境只对接一个 IAM 版本，grade_manager_id 的取值语义由该环境的
        BK_IAM_VERSION 决定，同一行记录不会同时持有 V3 与 V4 的 ID
    """

    app_code = models.CharField(max_length=20, help_text="应用代号")
    # V4 环境下该字段存管理空间 ID，取值语义由环境的 BK_IAM_VERSION 决定
    grade_manager_id = models.IntegerField(help_text="分级管理员 ID")
    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("app_code", "grade_manager_id")

    def __str__(self):
        return "{app_code}-{grade_manager_id}".format(app_code=self.app_code, grade_manager_id=self.grade_manager_id)


class ApplicationUserGroup(AuditedModel):
    """
    IAM 用户组与开发者中心应用的关系

    每个应用默认会有 3 个用户组（不可删除）：管理者，开发者，运营者

    note: 每个部署环境只对接一个 IAM 版本，user_group_id 的取值来自该环境的权限中心，
        同一行记录不会同时持有 V3 与 V4 的 ID
    """

    app_code = models.CharField(max_length=20, help_text="应用代号")
    role = models.IntegerField(default=ApplicationRole.DEVELOPER.value)
    # V3/V4 语义均为用户组 ID，取值来自当前环境对接的权限中心
    user_group_id = models.IntegerField(help_text="权限中心用户组 ID")
    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("app_code", "role")

    def __str__(self):
        return "{app_code}-{role}-{user_group_id}".format(
            app_code=self.app_code, role=ApplicationRole.get_choice_label(self.role), user_group_id=self.user_group_id
        )
