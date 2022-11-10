# -*- coding: utf-8 -*-


class NoDefaultClusterError(Exception):
    """未设置默认集群错误"""


class DuplicatedDefaultClusterError(Exception):
    """重复的默认集群错误"""


class SwitchDefaultClusterError(Exception):
    """切换默认集群出现异常"""
