# -*- coding: utf-8 -*-
import contextlib
import importlib
import threading
from typing import Callable, Dict

from urllib3.util import connection


class CustomLocalDnsResolver(threading.local):
    """Custom Local Dns Resolver
    支持在线程级自定义 Dns 记录
    """

    def __init__(self, dns_map=None):
        # 线程保存各自 dns_map，但是访问入口均为 dns_map
        self.dns_map = dns_map or {}


def get_patch_create_connection_with_dns(dns_resolver) -> Callable:
    """simply get patched create_connection"""

    # 保留原方法
    _orig_create_connection = getattr(importlib.import_module('urllib3.util.connection'), 'create_connection')

    def patched_create_connection(address, *args, **kwargs):
        """在 urllib3's create_connection 流程前解析 address"""
        domain, port = address
        # 当 _local_dns.dns_map 为空，对正常流程无影响
        host = dns_resolver.dns_map.get(domain, domain)
        return _orig_create_connection((host, port), *args, **kwargs)

    return patched_create_connection


_local_dns = CustomLocalDnsResolver()
# patch 全局 create_connection
connection.create_connection = get_patch_create_connection_with_dns(_local_dns)


@contextlib.contextmanager
def custom_resolver(dns_map: Dict):
    """A context manager which updates DNS resolver records, works on urllib3 module only"""
    _local_dns.dns_map = dns_map
    yield
    _local_dns.dns_map = {}
