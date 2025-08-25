# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import re
import socket
import ssl
from functools import wraps
from typing import Optional, Pattern, Tuple

from pydantic import VERSION, BaseModel

_endpoint_status_cache = {
    # well-known endpoints
    "registry.hub.docker.com": (True, True),
    "index.docker.io": (True, True),
    "quay.io": (True, True),
}


def cache_endpoint_status(func):
    @wraps(func)
    def is_secure_repository(self, *, timeout: Optional[float] = None):
        if self.url in _endpoint_status_cache:
            return _endpoint_status_cache[self.url]
        _endpoint_status_cache[self.url] = func(self, timeout=timeout)
        return _endpoint_status_cache[self.url]

    return is_secure_repository


class cached_property:
    """
    Decorator that converts a method with a single self argument into
    a property cached on the instance.
    """

    # NOTE: implementation borrowed from Django.
    # NOTE: we use fget, fset and fdel attributes to mimic @property.
    fset = fdel = None

    def __init__(self, fget):
        self.fget = fget
        self.__doc__ = getattr(fget, "__doc__")

    def __get__(self, instance, type=None):
        if instance is None:
            return self
        res = instance.__dict__[self.fget.__name__] = self.fget(instance)
        return res


class APIEndpoint(BaseModel):
    version: int = 2
    url: str
    official: bool = False

    class Config:
        arbitrary_types_allowed = True
        if VERSION.startswith("1."):
            keep_untouched = (cached_property,)
        else:
            ignored_types = (cached_property,)

    @cache_endpoint_status
    def is_secure_repository(self, *, timeout: Optional[float] = None) -> Tuple[bool, bool]:
        """Detect if the repository is secure

        returns Tuple[bool, bool], the first one mean if the server support https?,
                                    the second one mean if the ssl certificate is valid?
        """
        match = url_regex().match(self.url)
        if not match:
            return False, False

        parts = match.groupdict()
        hostname = parts.get("domain") or parts.get("ipv4") or parts.get("ipv6")
        port = int(parts.get("port") or 443)
        try:
            context = ssl.create_default_context()
            connection = socket.create_connection((hostname, port), timeout=timeout)
            sock = context.wrap_socket(connection, server_hostname=hostname)
            sock.getpeercert()
        except ssl.SSLError as e:
            if e.reason == "CERTIFICATE_VERIFY_FAILED":
                return True, False
            elif e.reason == "WRONG_VERSION_NUMBER":
                return False, False
            return False, False
        except socket.timeout:
            raise
        except OSError:
            return False, False
        return True, True

    @cached_property
    def api_base_url(self) -> str:
        match = url_regex().match(self.url)
        if not match:
            raise ValueError("Invalid Url")

        parts = match.groupdict()
        hostname = parts["domain"] or parts["ipv4"] or parts["ipv6"]

        port = parts["port"]
        if not port:
            port = "443" if self.is_secure_repository()[0] else "80"

        path = parts["path"] or ""
        return f"{hostname}:{port}{path}"


_url_regex_cache = None


def url_regex() -> Pattern[str]:
    global _url_regex_cache
    if _url_regex_cache is None:
        _url_regex_cache = re.compile(
            r"(?:(?P<scheme>[a-z][a-z0-9+\-.]+)://)?"  # scheme https://tools.ietf.org/html/rfc3986#appendix-A
            r"(?:(?P<user>[^\s:/]*)(?::(?P<password>[^\s/]*))?@)?"  # user info
            r"(?:"
            r"(?P<ipv4>(?:\d{1,3}\.){3}\d{1,3})|"  # ipv4
            r"(?P<ipv6>\[[A-F0-9]*:[A-F0-9:]+\])|"  # ipv6
            r"(?P<domain>[^\s/:?#]+)"  # domain, validation occurs later
            r")?"
            r"(?::(?P<port>\d+))?"  # port
            r"(?P<path>/[^\s?#]*)?"  # path
            r"(?:\?(?P<query>[^\s#]+))?"  # query
            r"(?:#(?P<fragment>\S+))?",  # fragment
            re.IGNORECASE,
        )
    return _url_regex_cache


OFFICIAL_ENDPOINT = APIEndpoint(url="registry.hub.docker.com", official=True)
