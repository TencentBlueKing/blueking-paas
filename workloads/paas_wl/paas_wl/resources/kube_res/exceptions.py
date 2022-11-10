# -*- coding: utf-8 -*-


class AppEntityNotFound(Exception):
    """Exception when required resource is not found in apiserver"""


class WatchKubeResourceError(Exception):
    """Raised when an error response was returned when performing a watch request"""


class APIServerVersionIncompatible(Exception):
    """Raised when apiserver does not support requested api_version"""
