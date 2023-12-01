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
import inspect
from typing import Callable, List, NoReturn, Optional, Union  # noqa: F401

from django.apps import AppConfig
from django.utils.module_loading import import_string

try:
    from django.urls import URLPattern, URLResolver
except ImportError:
    # Will be removed in Django 2.0
    from django.urls import RegexURLPattern as URLPattern
    from django.urls import RegexURLResolver as URLResolver


URL_PATTERNS_TYPE = List[Union[URLResolver, URLPattern]]


class AddonsUrlRegister:
    """register extra urlpatterns to the one provided"""

    def __init__(self, urlpatterns: URL_PATTERNS_TYPE):
        """
        :param urlpatterns: urlpatterns to be extended
        """
        self.urlpatterns = urlpatterns

    def register(self, url: Union[URLResolver, URLPattern]):
        self.urlpatterns.append(url)


class PlugableAppConfig(AppConfig):
    method: str = "contribute_to_app"

    def ready(self):
        __module__ = self.__module__
        for path in [__module__, f"{__module__}_ext"]:
            try:
                contribute = import_string(f"{path}.{self.method}")  # type: Callable[[str], NoReturn]
            except ImportError:
                continue
            if not callable(contribute):
                raise TypeError("contribute must be callable")
            if len(inspect.signature(contribute).parameters) != 1:
                raise RuntimeError("contribute should accept and only accept 1 parameter")
            break
        else:
            return

        contribute(self.name)


class ReplaceableFunction:
    """A dummy placeholder to register extra logic in other Edition"""

    def __init__(self, default_factory: Optional[Callable] = None):
        self.default_factory = default_factory
        self.handler: Optional[Callable] = None

    def __call__(self, *args, **kwargs):
        if self.handler is not None:
            return self.handler(*args, **kwargs)
        return self.default_factory() if self.default_factory else None

    def use(self, handler: Callable, force_replace: bool = False):
        """
        :param force_replace: relace the handler function even if it was set, default to False
        """
        if self.handler is not None and not force_replace:
            raise ValueError("Can only be bound once")
        self.handler = handler
        return handler
