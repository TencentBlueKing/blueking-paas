# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from paasng.accounts.constants import SiteRole
from paasng.accounts.models import UserProfile

from .base import ProtectedResource
from .tools import user_has_perm


class GlobalSiteResource(ProtectedResource):

    permissions = [
        ('visit_site', 'Can visit site'),
        ('visit_admin', 'Can visit admin pages'),
        # System-wide api permissions
        ('sysapi:read:applications', 'Can read application and modules infos'),
        ('sysapi:manage:applications', 'Can manage a application'),
        ('sysapi:read:services', 'Can read services infos'),
        ('sysapi:manage:light-applications', 'Can manage light application'),
        ('sysapi:manage:access_control', 'Can manage access_control strategies'),
        ('sysapi:read:db-credential', 'Can read db-credential'),
        ('sysapi:bind:db-service', 'Can bind db-service'),
        # admin页面权限
        ('admin:read:application', 'Can view application in admin'),
        ('admin:modify:application', 'Can modify application in admin'),
        ('admin:manage:user', 'Can manage user in admin'),
        ('admin:manage:workloads', 'Can manage Workloads Resource in admin'),
    ]

    def _get_role_of_user(self, user, obj):
        """Get user role of site"""
        if not user.is_authenticated:
            return 'nobody'

        try:
            profile = UserProfile.objects.get_profile(user)
        except UserProfile.DoesNotExist:
            return 'nobody'

        return SiteRole(profile.role).name.lower()


global_site_resource = GlobalSiteResource()
global_site_resource.add_nobody_role()
global_site_resource.add_role(
    'user',
    {
        'visit_site': True,
        'visit_admin': False,
        'sysapi:read:applications': False,
        'sysapi:manage:applications': False,
        'sysapi:read:services': False,
        'sysapi:manage:access_control': False,
        'sysapi:manage:light-applications': False,
        'sysapi:read:db-credential': False,
        'sysapi:bind:db-service': False,
        # admin页面权限
        "admin:read:application": False,
        "admin:modify:application": False,
        "admin:manage:user": False,
        "admin:manage:workloads": False,
    },
)
global_site_resource.add_role(
    'admin',
    {
        'visit_site': True,
        'visit_admin': True,
        'sysapi:read:applications': False,
        'sysapi:manage:applications': False,
        'sysapi:read:services': False,
        'sysapi:manage:access_control': False,
        'sysapi:manage:light-applications': False,
        'sysapi:read:db-credential': False,
        'sysapi:bind:db-service': False,
        # admin页面权限
        "admin:read:application": True,
        "admin:modify:application": True,
        "admin:manage:user": True,
        "admin:manage:workloads": True,
    },
)
global_site_resource.add_role(
    'super_user',
    {
        'visit_site': True,
        'visit_admin': True,
        'sysapi:read:applications': False,
        'sysapi:manage:applications': False,
        'sysapi:read:services': False,
        'sysapi:manage:access_control': False,
        'sysapi:manage:light-applications': False,
        'sysapi:read:db-credential': False,
        'sysapi:bind:db-service': False,
        # admin页面权限
        "admin:read:application": True,
        "admin:modify:application": True,
        "admin:manage:user": True,
        "admin:manage:workloads": True,
    },
)
global_site_resource.add_role(
    'banned_user',
    {
        'visit_site': False,
        'visit_admin': False,
        'sysapi:read:applications': False,
        'sysapi:manage:applications': False,
        'sysapi:read:services': False,
        'sysapi:manage:access_control': False,
        'sysapi:manage:light-applications': False,
        'sysapi:read:db-credential': False,
        'sysapi:bind:db-service': False,
        # admin页面权限
        "admin:read:application": False,
        "admin:modify:application": False,
        "admin:manage:user": False,
        "admin:manage:workloads": False,
    },
)

# System api roles
global_site_resource.add_role(
    'system_api_basic_reader',
    {
        'visit_site': True,
        'visit_admin': False,
        'sysapi:read:applications': True,
        'sysapi:manage:applications': False,
        'sysapi:read:services': True,
        'sysapi:manage:access_control': False,
        'sysapi:manage:light-applications': False,
        'sysapi:read:db-credential': False,
        'sysapi:bind:db-service': False,
        # admin页面权限
        "admin:read:application": False,
        "admin:modify:application": False,
        "admin:manage:user": False,
        "admin:manage:workloads": False,
    },
)

# System api roles
global_site_resource.add_role(
    'system_api_basic_maintainer',
    {
        'visit_site': True,
        'visit_admin': False,
        'sysapi:read:applications': True,
        'sysapi:manage:applications': True,
        'sysapi:read:services': True,
        'sysapi:manage:access_control': True,
        'sysapi:manage:light-applications': False,
        'sysapi:read:db-credential': False,
        'sysapi:bind:db-service': False,
        # admin页面权限
        "admin:read:application": False,
        "admin:modify:application": False,
        "admin:manage:user": False,
        "admin:manage:workloads": False,
    },
)

global_site_resource.add_role(
    'system_api_light_app_maintainer',
    {
        'visit_site': True,
        'visit_admin': False,
        'sysapi:read:applications': True,
        'sysapi:manage:applications': False,
        'sysapi:read:services': True,
        'sysapi:manage:access_control': False,
        'sysapi:manage:light-applications': True,
        'sysapi:read:db-credential': False,
        'sysapi:bind:db-service': False,
        # admin页面权限
        "admin:read:application": False,
        "admin:modify:application": False,
        "admin:manage:user": False,
        "admin:manage:workloads": False,
    },
)

global_site_resource.add_role(
    'system_api_lesscode',
    {
        'visit_site': True,
        'visit_admin': False,
        'sysapi:read:applications': True,
        'sysapi:manage:applications': True,
        'sysapi:read:services': True,
        'sysapi:manage:access_control': False,
        'sysapi:manage:light-applications': False,
        'sysapi:read:db-credential': True,
        'sysapi:bind:db-service': True,
        # admin页面权限
        "admin:read:application": False,
        "admin:modify:application": False,
        "admin:manage:user": False,
        "admin:manage:workloads": False,
    },
)


def site_perm_required(perm_name):
    """This decorator can be used on viewset methods"""
    if not global_site_resource.has_permission(perm_name):
        raise ValueError(f'"{perm_name}" is not a valid permission name for Site')

    def decorated(func):
        def view_func(self, request, *args, **kwargs):
            if not user_has_perm(request.user, perm_name, 'site'):
                raise PermissionDenied('You are not allowed to do this operation.')

            return func(self, request, *args, **kwargs)

        return view_func

    return decorated


class SitePermission(BasePermission):
    def __init__(self, perm_name):
        if not global_site_resource.has_permission(perm_name):
            raise ValueError(f'"{perm_name}" is not a valid permission name for Site')
        self.perm_name = perm_name

    def has_permission(self, request, *args, **kwargs):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if not user_has_perm(request.user, self.perm_name, 'site'):
            raise PermissionDenied('You are not allowed to do this operation.')
        return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if not user_has_perm(request.user, self.perm_name, 'site'):
            raise PermissionDenied('You are not allowed to do this operation.')
        return True

    def __call__(self, *args, **kwargs):
        return self
