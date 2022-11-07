# -*- coding: utf-8 -*-
import logging

from django.http import HttpRequest
from rest_framework import permissions

from paas_wl.platform.applications.struct_models import Application, SitePermissions

logger = logging.getLogger(__name__)


def application_perm_class(perm_name: str):
    """A factory function which generates a Permission class for DRF permission check"""

    class Permission(permissions.BasePermission):
        """Check if an user has permission to operate an application"""

        def has_object_permission(self, request: HttpRequest, view, obj: Application):
            assert isinstance(obj, Application), 'Only support "Application" object'

            # TODO: Support permission check by requesting remote endpoints
            app_perms = request.perms_in_place.get_application_perms(obj)
            ret = app_perms.check_allowed(perm_name)
            logger.debug('Permission check result, user: %s, obj: %s, retsult: %s', request.user, obj, ret)
            return ret

    return Permission


def site_perm_class(perm_name: str):
    """A factory function which generates a Permission class for DRF permission check"""

    class Permission(permissions.BasePermission):
        """Check if an user has permission on site"""

        def has_permission(self, request, view):
            site_perms: SitePermissions = request.perms_in_place.site_perms
            if site_perms is None:
                return False
            return site_perms.check_allowed(perm_name)

        def has_object_permission(self, request, view, obj):
            return super().has_permission(request, view)

    return Permission
