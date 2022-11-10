# -*- coding: utf-8 -*-
import uuid

from django.conf import settings
from werkzeug.local import Local as _Local
from werkzeug.local import release_local

_local = _Local()


def new_request_id():
    return uuid.uuid4().hex


class Singleton(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)  # type: ignore
        return cls._instance


class Local(Singleton):
    """local 对象，配合中间件 RequestProvider 使用"""

    @property
    def request(self):
        """获取全局 request 对象"""
        request = getattr(_local, 'request', None)
        return request

    @request.setter
    def request(self, value):
        """设置全局 request 对象"""
        _local.request = value

    @property
    def request_id(self):
        if self.request:
            return self.request.request_id

        return new_request_id()

    def get_http_request_id(self):
        """从接入层获取 request_id，若不存在，则新建并写入"""
        request_id = self.request.META.get(settings.REQUEST_ID_META_KEY, '')
        if not request_id:
            request_id = new_request_id()
            self.request.META[settings.REQUEST_ID_META_KEY] = request_id

        return request_id

    def release(self):
        release_local(_local)


local = Local()
