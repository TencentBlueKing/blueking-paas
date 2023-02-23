# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import uuid

from django.conf import settings
from werkzeug.local import Local as _Local
from werkzeug.local import release_local

_local = _Local()


def new_request_id():
    return uuid.uuid4().hex


class Singleton:
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
