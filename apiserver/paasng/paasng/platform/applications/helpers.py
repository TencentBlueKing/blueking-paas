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

from paasng.infras.iam.client import BKIAMClient
from paasng.infras.iam.constants import NEVER_EXPIRE_DAYS
from paasng.infras.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.platform.applications.models import Application
from paasng.utils.basic import get_username_by_bkpaas_user_id

logger = logging.getLogger(__name__)


def register_builtin_user_groups_and_grade_manager(application: Application):
    """
    默认为每个新建的蓝鲸应用创建三个用户组（管理者，开发者，运营者），以及该应用对应的分级管理员
    将 创建者 添加到 管理者用户组 以获取应用的管理权限，并添加为 分级管理员成员 以获取审批其他用户加入各个用户组的权限
    """
    cli = BKIAMClient()
    creator = get_username_by_bkpaas_user_id(application.creator)

    # 1. 创建分级管理员，并记录分级管理员 ID
    grade_manager_id = cli.create_grade_managers(application.code, application.name, creator)
    ApplicationGradeManager.objects.create(app_code=application.code, grade_manager_id=grade_manager_id)

    # 2. 将创建者，添加为分级管理员的成员
    cli.add_grade_manager_members(grade_manager_id, [creator])

    # 3. 创建默认的 管理者，开发者，运营者用户组
    user_groups = cli.create_builtin_user_groups(grade_manager_id, application.code)
    ApplicationUserGroup.objects.bulk_create(
        [
            ApplicationUserGroup(app_code=application.code, role=group["role"], user_group_id=group["id"])
            for group in user_groups
        ]
    )

    # 4. 为默认的三个用户组授权
    cli.grant_user_group_policies(application.code, application.name, user_groups)

    # 5. 将创建者添加到管理者用户组，返回数据中第一个即为管理者用户组信息
    cli.add_user_group_members(user_groups[0]["id"], [creator], NEVER_EXPIRE_DAYS)
