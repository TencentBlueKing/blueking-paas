"""Utilities for mocks"""
from contextlib import contextmanager
from types import MethodType
from typing import Callable
from unittest import mock


class mockable_function:
    """增加一个快捷 mock 函数入口"""

    def __init__(self, func: Callable):
        self._func = func

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def __get__(self, obj, obj_type=None):
        """实现描述符协议，兼容装饰类方法时的情况"""
        if obj is None:
            return self
        return MethodType(self, obj)

    def mock(self, *args, **kwargs):
        """返回 Mock 当前函数的上下文管理器"""

        @contextmanager
        def _mocking_func():
            mocked_obj = mock.MagicMock(*args, **kwargs)
            orig_func = self._func
            self._func = mocked_obj
            try:
                yield
            finally:
                self._func = orig_func

        return _mocking_func()
