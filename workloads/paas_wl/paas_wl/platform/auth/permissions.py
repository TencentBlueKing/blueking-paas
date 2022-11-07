# -*- coding: utf-8 -*-
from rest_framework import permissions


class IsInternalAdmin(permissions.BasePermission):
    """Object-level permission to allow only internal admin user to access it"""

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return False
