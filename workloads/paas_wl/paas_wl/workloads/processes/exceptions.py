"""Custom exceptions for processes module"""


class ProcessOperationTooOften(Exception):
    """进程操作过于频繁"""


class ProcessNotFound(Exception):
    """Unable to find the process"""


class ScaleProcessError(Exception):
    """Unable to scale process due to internal errors"""
