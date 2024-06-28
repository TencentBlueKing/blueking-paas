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

from django.db.models import Q

from tests.utils.auth import create_user


class StubApplicationPermission:
    """应用权限（单元测试用）"""

    def can_view_basic_info(self, *args, **kwargs) -> bool:
        return True

    def can_edit_basic_info(self, *args, **kwargs) -> bool:
        return True

    def can_delete_application(self, *args, **kwargs) -> bool:
        return True

    def can_manage_members(self, *args, **kwargs) -> bool:
        return True

    def can_manage_access_control(self, *args, **kwargs) -> bool:
        return True

    def can_manage_app_market(self, *args, **kwargs) -> bool:
        return True

    def can_data_statistics(self, *args, **kwargs) -> bool:
        return True

    def can_basic_develop(self, *args, **kwargs) -> bool:
        return True

    def can_manage_cloud_api(self, *args, **kwargs) -> bool:
        return True

    def can_view_alert_records(self, *args, **kwargs) -> bool:
        return True

    def can_edit_alert_policy(self, *args, **kwargs) -> bool:
        return True

    def can_manage_addons_services(self, *args, **kwargs) -> bool:
        return True

    def can_manage_env_protection(self, *args, **kwargs) -> bool:
        return True

    def can_manage_module(self, *args, **kwargs) -> bool:
        return True

    def gen_user_app_filters(self, username):
        """生成用户有权限的应用 Django 过滤条件"""
        from paasng.platform.applications.models import ApplicationMembership

        app_ids = ApplicationMembership.objects.filter(user=create_user(username)).values_list(
            "application_id", flat=True
        )
        return Q(id__in=app_ids)

    def gen_develop_app_filters(self, username):
        """生成用户有开发者权限的应用 Django 过滤条件"""
        from paasng.platform.applications.constants import ApplicationRole
        from paasng.platform.applications.models import ApplicationMembership

        app_ids = ApplicationMembership.objects.filter(
            user=create_user(username), role__in=[ApplicationRole.ADMINISTRATOR, ApplicationRole.DEVELOPER]
        ).values_list("application_id", flat=True)
        return Q(id__in=app_ids)
