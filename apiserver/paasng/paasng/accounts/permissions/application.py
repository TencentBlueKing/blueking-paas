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
"""Permissions for application
"""
from typing import Union

from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application, ApplicationMembership
from paasng.platform.modules.models import Module

from .base import ProtectedResource
from .tools import user_has_perm, user_has_perms


class ApplicationResource(ProtectedResource):

    permissions = [
        ('view_application', 'Can view application'),
        ('checkout_source', 'Can checkout source'),
        ('commit_source', 'Can checkout source'),
        ('manage_services', 'Can checkout source'),
        ('manage_processes', 'Can manage process'),
        ('view_logs', 'Can view logs'),
        ('manage_deploy', 'Can manage deployments'),
        ('manage_env_protection', 'Can manage env protection'),
        ('manage_members', 'Can manage memberships'),
        ('manage_product', 'Can manage product which is related to this application'),
        ('review_app', 'Can review app when it will be online'),
        ('edit_app', 'Can edit app, such as name'),
        ('delete_app', 'Can delete app'),
        ('manage_cloud_api', 'Can manage cloud api'),
        ('manage_access_control', 'Can manage access control'),
    ]

    def _get_role_of_user(self, user, obj):
        """Get the role of application"""
        role = get_user_app_role(user, obj)
        return ApplicationRole(role).name.lower()


application_resource = ApplicationResource()

application_resource.add_nobody_role()
application_resource.add_role(
    'administrator',
    {
        'view_application': True,
        'checkout_source': True,
        'commit_source': True,
        'manage_services': True,
        'manage_processes': True,
        'view_logs': True,
        'manage_deploy': True,
        'manage_env_protection': True,
        'manage_members': True,
        'manage_product': True,
        'review_app': True,
        'edit_app': True,
        'delete_app': True,
        'manage_cloud_api': True,
        'manage_access_control': True,
    },
)
application_resource.add_role(
    'developer',
    {
        'view_application': True,
        'checkout_source': True,
        'commit_source': True,
        'manage_services': True,
        'manage_processes': True,
        'view_logs': True,
        'manage_deploy': True,
        'manage_env_protection': False,
        'manage_members': False,
        'manage_product': True,
        'review_app': False,
        'edit_app': True,
        'delete_app': False,
        'manage_cloud_api': True,
        'manage_access_control': True,
    },
)
application_resource.add_role(
    'operator',
    {
        'view_application': True,
        'checkout_source': False,
        'commit_source': False,
        'manage_services': False,
        'manage_processes': False,
        'view_logs': False,
        'manage_deploy': False,
        'manage_env_protection': False,
        'manage_members': False,
        'manage_product': True,
        'review_app': True,
        'edit_app': True,
        'delete_app': False,
        'manage_cloud_api': True,
        'manage_access_control': True,
    },
)


def get_user_app_role(user, obj: Union[Application, Module]):
    # Module 权限完全兼容 Application
    if isinstance(obj, Module):
        application = obj.application
    else:
        application = obj

    try:
        # Currently, user can only have one role
        membership = ApplicationMembership.objects.get(application=application, user=user.pk)
    except (ApplicationMembership.DoesNotExist, ApplicationMembership.MultipleObjectsReturned):
        return ApplicationRole.NOBODY.value
    return membership.role


def application_perm_class(perm_name):
    """A factory function which generates a Permission class for DRF permission check"""
    if perm_name not in application_resource._permissions:
        raise ValueError('"%s" is not a valid permission name for Application' % perm_name)

    class Permission(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            return user_has_perm(request.user, perm_name, obj)

    return Permission


def check_application_perms(user, perm_names, application):
    for perm_name in perm_names:
        if perm_name not in application_resource._permissions:
            raise ValueError('"%s" is not a valid permission name for Application' % perm_name)
    if not user_has_perms(user, perm_names, application):
        raise PermissionDenied('You are not allowed to do this operation.')


def application_perm_required(perm_name):
    """This decorator can only be used when these conditions are meet:

    - decorated func if a method in ViewSet
    - there is a "code" kwargs in request path which represents application code
    """
    if perm_name not in application_resource._permissions:
        raise ValueError('"%s" is not a valid permission name for Application' % perm_name)

    def decorated(func):
        def view_func(self, request, *args, **kwargs):
            application = get_object_or_404(Application, code=kwargs['code'])
            if not user_has_perm(request.user, perm_name, application):
                raise PermissionDenied('You are not allowed to do this operation.')

            return func(self, request, *args, **kwargs)

        return view_func

    return decorated


def application_perm_required_with_uuid(perm_name):
    """This decorator can only be used when these conditions are meet:

    - decorated func if a method in ViewSet
    - there is a "application_id" kwargs in request.data
    """
    if perm_name not in application_resource._permissions:
        raise ValueError('"%s" is not a valid permission name for Application' % perm_name)

    def decorated(func):
        def view_func(self, request, *args, **kwargs):
            application = get_object_or_404(Application, pk=request.data.get('application_id'))
            if not user_has_perm(request.user, perm_name, application):
                raise PermissionDenied('You are not allowed to do this operation.')

            return func(self, request, *args, **kwargs)

        return view_func

    return decorated
