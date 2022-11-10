# -*- coding: utf-8 -*-


class ReleaseMissingError(Exception):
    """release missing"""


class BuildMissingError(Exception):
    """build missing"""


class CommandRerunError(Exception):
    """Command 重复执行异常"""
