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

from paasng.infras.iam.base.constants import IAMVersion
from paasng.infras.iam.constants import NEVER_EXPIRE_DAYS
from paasng.infras.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.infras.iam.shim import get_iam_version, get_management_backend
from paasng.platform.applications.models import Application
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.utils.basic import get_username_by_bkpaas_user_id

logger = logging.getLogger(__name__)


def register_builtin_user_groups_and_grade_manager(application: Application, add_creator_to_admin_group: bool = True):
    """
    默认为每个新建的蓝鲸应用创建三个用户组（管理者，开发者，运营者），以及该应用对应的分级管理员
    将 创建者 添加到 管理者用户组 以获取应用的管理权限，并添加为 分级管理员成员 以获取审批其他用户加入各个用户组的权限

    :param add_creator_to_admin_group: V4 下是否将创建者加入管理者用户组，V3 始终加入
    """
    tenant_id = get_tenant_id_for_app(application.code)
    creator = get_username_by_bkpaas_user_id(application.creator)
    backend = get_management_backend(tenant_id, operator=creator)

    # 1. 创建分级管理员 / 管理空间，并记录 ID（V4 语义为管理空间 ID）
    space_id = backend.create_management_space(
        application.code,
        application.name,
        init_members=[creator],
    )
    ApplicationGradeManager.objects.create(app_code=application.code, grade_manager_id=space_id, tenant_id=tenant_id)

    # 2. 将创建者添加为分级管理员的成员。V4 的 managers 已在创建空间时写入，
    #    且 V4 暂无空间成员增删接口，这里不再补调，避免把创建流程打断。
    if get_iam_version() == IAMVersion.V3:
        backend.add_management_space_members(space_id, [creator], operator=creator)

    # 3. 创建默认的 管理者，开发者，运营者用户组。
    #    V4 创建时一次性写入权限范围与管理员组成员，减少中间失败态。
    user_groups = backend.create_builtin_user_groups(
        space_id,
        application.code,
        app_name=application.name,
        init_members=[creator] if add_creator_to_admin_group else None,
    )
    ApplicationUserGroup.objects.bulk_create(
        [
            ApplicationUserGroup(
                app_code=application.code, role=group.role, user_group_id=group.id, tenant_id=tenant_id
            )
            for group in user_groups
        ]
    )

    # 4. V3 需要单独授权并把创建者加入管理者用户组。
    #    V4 已在创建用户组时完成授权与加成员，且没有给已有组补授权的接口。
    if get_iam_version() == IAMVersion.V3:
        backend.grant_user_group_policies(application.code, application.name, user_groups)
        backend.add_user_group_members(user_groups[0].id, [creator], NEVER_EXPIRE_DAYS, operator=creator)
