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

from urllib.parse import urlparse

from django.conf import settings
from rest_framework.exceptions import ValidationError

from paasng.platform.sourcectl.source_types import docker_registry_config

_ALLOWED_SCHEMES = {"http", "https"}
_STANDARD_PORTS = {80, 443}
_DEFAULT_PORT_BY_SCHEME = {"http": 80, "https": 443}


def validate_image_url(url: str) -> str:
    """检查镜像地址(判断是否支持第三方镜像)"""
    default_registry = docker_registry_config.default_registry
    allow_third_party_registry = docker_registry_config.allow_third_party_registry
    if not allow_third_party_registry and not url.startswith(default_registry):
        raise ValidationError(f"`{url}` is not supported, please use image of `{default_registry}`")
    return url


def validate_download_url(url: str) -> None:
    """基于白名单校验源码包下载地址，防止 SSRF。

    校验规则：

    1. `SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS` 未配置或为空时，拒绝所有请求
    2. 协议必须为 ``http`` 或 ``https``，且端口必须为标准端口
    3. 主机名必须在 ``SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS`` 白名单中

    :param url: 待校验的下载地址
    :raises ValidationError: 当 URL 未通过安全校验时抛出
    """
    allowed_hosts: list[str] = getattr(settings, "SRC_PACKAGE_UPLOAD_ALLOWED_HOSTS", [])
    if not allowed_hosts:
        raise ValidationError("源码包 URL 上传功能未开启，请联系管理员")

    try:
        parsed = urlparse(url)
    except ValueError:
        raise ValidationError("URL 格式不合法")

    # 校验协议与端口
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValidationError(f"不允许的协议 '{scheme}'，仅支持 http 和 https")
    port = parsed.port or _DEFAULT_PORT_BY_SCHEME.get(scheme)
    if port not in _STANDARD_PORTS:
        raise ValidationError(f"不允许的端口 {port}，仅支持标准端口 80 和 443")

    # 校验主机名
    hostname = parsed.hostname
    if not hostname:
        raise ValidationError("URL 必须包含有效的主机名")
    allowed_hosts_lower = [h.lower() for h in allowed_hosts]
    if hostname.lower() not in allowed_hosts_lower:
        raise ValidationError(f"主机 '{hostname}' 不在允许的白名单中")
