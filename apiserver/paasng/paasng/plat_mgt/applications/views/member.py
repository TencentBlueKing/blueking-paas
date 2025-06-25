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


from collections import defaultdict

from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.helpers import (
    add_role_members,
    fetch_application_members,
    fetch_role_members,
    fetch_user_main_role,
    remove_user_all_roles,
)
from paasng.plat_mgt.applications import serializers as slzs
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application, ApplicationMembership, JustLeaveAppManager
from paasng.platform.applications.signals import application_member_updated
from paasng.platform.applications.tasks import sync_developers_to_sentry
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.error_codes import error_codes


class ApplicationMemberViewSet(viewsets.GenericViewSet):
    """平台管理 - 应用成员管理 API"""

    queryset = ApplicationMembership.objects.all()
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.applications.members"],
        responses={status.HTTP_200_OK: slzs.ApplicationMembershipListOutputSLZ(many=True)},
    )
    def list(self, request, app_code):
        """获取指定应用的成员列表"""
        application = get_object_or_404(Application, code=app_code)
        members = fetch_application_members(application.code)
        slz = slzs.ApplicationMembershipListOutputSLZ(members, many=True)
        return Response(data=slz.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.applications.members"],
        request_body=slzs.ApplicationMembershipCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: None},
    )
    def create(self, request, app_code):
        """添加成员"""

        application = get_object_or_404(Application, code=app_code)
        slz = slzs.ApplicationMembershipCreateInputSLZ(data=request.data, many=True)
        slz.is_valid(raise_exception=True)

        role_members_map = defaultdict(list)
        for info in slz.data:
            for role in info["roles"]:
                role_members_map[role["id"]].append(info["user"]["username"])

        try:
            for role, members in role_members_map.items():
                add_role_members(application.code, role, members)
        except BKIAMGatewayServiceError as e:
            raise error_codes.CREATE_APP_MEMBERS_ERROR.f(e.message)

        application_member_updated.send(sender=application, application=application)
        sync_developers_to_sentry.delay(application.id)
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.applications.members"],
        request_body=slzs.ApplicationMembershipUpdateInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, app_code, user_id):
        """更新成员"""
        application = get_object_or_404(Application, code=app_code)
        slz = slzs.ApplicationMembershipUpdateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        target_role = ApplicationRole(slz.data["role"]["id"])
        username = get_username_by_bkpaas_user_id(user_id)

        # 获取用户当前角色
        current_role = fetch_user_main_role(application.code, username)

        # 只有当角色发生变化的时候才进行检查和更新
        if current_role != target_role:
            self.check_admin_count(application.code, username)

            try:
                remove_user_all_roles(application.code, username)
                add_role_members(application.code, target_role, username)
            except BKIAMGatewayServiceError as e:
                raise error_codes.UPDATE_APP_MEMBERS_ERROR.f(e.message)

            sync_developers_to_sentry.delay(application.id)
            application_member_updated.send(sender=application, application=application)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.applications.members"],
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, app_code, user_id):
        """删除成员"""
        application = get_object_or_404(Application, code=app_code)

        username = get_username_by_bkpaas_user_id(user_id)
        self.check_admin_count(application.code, username)
        try:
            remove_user_all_roles(application.code, username)
        except BKIAMGatewayServiceError as e:
            raise error_codes.DELETE_APP_MEMBERS_ERROR.f(e.message)

        # 将该应用 Code 标记为刚退出，避免出现退出用户组，权限中心权限未同步的情况
        JustLeaveAppManager(username).add(application.code)

        sync_developers_to_sentry.delay(application.id)
        application_member_updated.send(sender=application, application=application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_roles(self, request):
        """查看所有角色列表"""
        return Response({"results": ApplicationRole.get_django_choices()})

    def check_admin_count(self, app_code: str, username: str):
        # Check whether the application has at least one administrator when the membership was deleted
        administrators = fetch_role_members(app_code, ApplicationRole.ADMINISTRATOR)
        if len(administrators) <= 1 and username in administrators:
            raise error_codes.MEMBERSHIP_DELETE_FAILED
