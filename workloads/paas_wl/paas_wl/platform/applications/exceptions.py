# -*- coding: utf-8 -*-


class BasePlatformException(Exception):
    """Base exception type for platform module"""


class InstanceInPlaceNotFound(Exception):
    """A requested instance-in-place was not found"""


class PermInPlaceNotFound(Exception):
    """A requested perm-in-place was not found"""


class UnsupportedPermissionName(Exception):
    """A requested permission name is not supported"""


class AppSubResourceNotFound(Exception):
    """Error when application's sub-resource(module, env) can not be found in structured app"""
