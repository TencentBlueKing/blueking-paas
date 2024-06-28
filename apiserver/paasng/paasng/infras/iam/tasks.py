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

from celery import shared_task

from paasng.infras.iam.client import BKIAMClient
from paasng.infras.iam.members.models import ApplicationGradeManager, ApplicationUserGroup


@shared_task
def add_monitoring_space_permission(app_code: str, app_name: str, bk_space_id: str):
    """
    给应用添加蓝鲸监控空间相关的权限，目前包括监控平台、日志平台权限

    :param app_code: 应用ID
    :param app_name: 应用名称
    :param bk_space_id: 蓝鲸监控空间ID
    """
    cli = BKIAMClient()

    # 1. 更新分级管理员的授权范围
    grade_manager_id = ApplicationGradeManager.objects.get(app_code=app_code).grade_manager_id
    cli.update_grade_managers_with_bksaas_space(grade_manager_id, app_code, app_name, bk_space_id)

    user_groups = ApplicationUserGroup.objects.filter(app_code=app_code).order_by("role")
    user_groups_list = [{"id": user_group.user_group_id, "role": user_group.role} for user_group in user_groups]

    # 2. 给应用的管理员、开发者、运营者添加监控平台、日志平台权限
    cli.grant_user_group_policies_in_bk_monitor(bk_space_id, app_name, user_groups_list)
    cli.grant_user_group_policies_in_bk_log(bk_space_id, app_name, user_groups_list)
