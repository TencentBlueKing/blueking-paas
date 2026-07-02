# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import base64
import re
from typing import Collection, Dict, Mapping, NamedTuple, Sequence
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_str
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError as DRFValidationError

from paasng.utils.file import path_may_escape
from paasng.utils.moby_distribution.registry.utils import parse_image

# k8s 广泛使用的命名规范, 仅允许小写字母、数字和连字符, 最大长度 63
# 参考 https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#rfc-1035-label-names
DNS_SAFE_PATTERN = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"
DNS_MAX_LENGTH = 63

RE_APP_CODE = re.compile(r"^[a-z0-9-]{1,16}$")
RE_APP_SEARCH = re.compile("[\u4300-\u9fa5\\w_\\-\\d]{1,20}")

RE_CONFIG_VAR_KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")


@deconstructible
class DnsSafeNameValidator:
    """DNS name safe validator"""

    def __init__(self, resource_type: str):
        self.resource_type = resource_type
        self.message = f"{self.resource_type} 不能以 - 或数字开头或结尾, 且不能为纯数字"
        self.validator = RegexValidator("^(?![0-9]+.*$)(?!-)[a-zA-Z0-9-]{,63}(?<!-)$", message=self.message)

    def __call__(self, value):
        value = force_str(value)
        self.validator(value)


@deconstructible
class ReservedWordValidator:
    """Reserved word validator"""

    def __init__(self, resource_type: str):
        self.resource_type = resource_type
        self.reserved_word = ["-dot-", "0us0", "--", "-m-"]
        self.message = f"{self.resource_type} 不能包含保留字 {self.reserved_word}"
        self.validator = RegexValidator("|".join(self.reserved_word), message=self.message, inverse_match=True)

    def __call__(self, value):
        value = force_str(value)
        self.validator(value)


@deconstructible
class Base64Validator:
    def __call__(self, value):
        try:
            base64.b64decode(value)
        except Exception:  # noqa: BLE001
            raise ValidationError("content is not a base64 encoded obj.")


def str2bool(value):
    true_values = {
        "t",
        "T",
        "y",
        "Y",
        "yes",
        "YES",
        "true",
        "True",
        "TRUE",
        "on",
        "On",
        "ON",
        "1",
    }
    false_values = {
        "f",
        "F",
        "n",
        "N",
        "no",
        "NO",
        "false",
        "False",
        "FALSE",
        "off",
        "Off",
        "OFF",
        "0",
    }
    if value in true_values:
        return True
    elif value in false_values:
        return False
    else:
        raise ValueError(f"Given value({value}) not valid!")


# 进程名称会用于 k8s 资源命名, k8s 资源命名要求 dns-safe, 因此目前限制进程名称只能有小写字母、数字和连字符
# Note: 这个约束比 heroku 和 cnb 更严格, 未来如果有需求，可以再考虑调整这个限制, CNB/heroku 的限制是: ([a-zA-Z0-9_-]+
PROC_TYPE_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9])*$")
PROC_TYPE_MAX_LENGTH = 12

# match_allowed_hosts() 依赖此映射，将省略端口与显式默认端口视为同一个主机。
# validate_download_url() 与 validate_repo_url() 在校验带协议 URL 的主机白名单时会使用该行为。
DEFAULT_PORT_BY_SCHEME = {"http": 80, "https": 443, "git": 9418, "svn": 3690, "ssh": 22}
SUPPORTED_REPO_URL_SCHEMES = ("http", "https", "git", "svn", "ssh")


class URLHostInfo(NamedTuple):
    scheme: str
    hostname: str
    port: int | None


class UnsupportedURLScheme(ValueError):
    """URL 使用了不允许的协议。"""

    def __init__(self, scheme: str, allowed_schemes: Collection[str]):
        self.scheme = scheme
        self.allowed_schemes = tuple(allowed_schemes)
        super().__init__(f"Invalid url: only support {'/'.join(self.allowed_schemes)} scheme")


def parse_url_host(url: str, allowed_schemes: Collection[str]) -> URLHostInfo:
    """解析 URL 并返回标准化后的主机信息。

    该函数为白名单校验集中处理 URL 主机解析与基础格式校验。若调用方直接使用
    ``urlparse()``，还需要在各处重复检查协议、主机、协议是否允许，以及端口是否
    为合法整数。将这些规则收敛到这里，可以避免不同校验函数之间的行为漂移。
    """
    try:
        parsed_url = urlparse(url)
    except Exception:  # noqa: BLE001
        raise ValueError("Invalid url")

    scheme, hostname = parsed_url.scheme.lower(), parsed_url.hostname
    if not scheme or not hostname:
        raise ValueError("Invalid url")

    if scheme not in allowed_schemes:
        raise UnsupportedURLScheme(scheme=scheme, allowed_schemes=allowed_schemes)

    try:
        port = parsed_url.port
    except ValueError:
        raise ValueError("Invalid url")

    return URLHostInfo(scheme=scheme, hostname=hostname, port=port)


def parse_domain_host(domain: str) -> URLHostInfo:
    """从不包含协议的域名字符串中解析主机信息。"""
    parsed_domain = urlparse(f"//{domain}")
    hostname = parsed_domain.hostname
    if not hostname:
        raise ValueError("Invalid host")

    try:
        port = parsed_domain.port
    except ValueError:
        raise ValueError("Invalid host")

    return URLHostInfo(scheme="", hostname=hostname, port=port)


def match_allowed_hosts(
    hostname: str,
    port: int | None,
    allowed_hosts: Sequence[str] | None,
    scheme: str = "",
    default_port_by_scheme: Mapping[str, int] | None = None,
) -> bool:
    """检查主机与可选端口是否命中白名单。

    ``allowed_hosts`` 为 None 时表示不限制主机；空列表表示不放通任何主机。

    :param hostname: 已解析的主机名，不包含端口。
    :param port: 已解析的端口。``None`` 表示 URL 或域名中省略了端口。
    :param allowed_hosts: 主机白名单条目，可包含端口。``None`` 表示允许任意主机。
    :param scheme: URL 协议，用于查询默认端口；不含协议的域名场景保持为空字符串。
    :param default_port_by_scheme: 可选的协议到默认端口映射，供自定义协议场景覆盖。
    :return: 主机是否命中白名单。
    """
    if allowed_hosts is None:
        return True
    if not allowed_hosts:
        return False

    default_port_by_scheme = default_port_by_scheme or DEFAULT_PORT_BY_SCHEME
    default_port = default_port_by_scheme.get(scheme)

    if port:
        to_check_hosts = [f"{hostname}:{port}"]
        if port == default_port:
            to_check_hosts.append(hostname)
    else:
        to_check_hosts = [hostname]
        if default_port:
            to_check_hosts.append(f"{hostname}:{default_port}")

    allowed_hosts_lower = [h.lower() for h in allowed_hosts]
    return any(host.lower() in allowed_hosts_lower for host in to_check_hosts)


def validate_procfile(procfile: Dict[str, str]) -> Dict[str, str]:
    """Validate proc type format
    :param procfile:
    :return: validated procfile, which all key is lower case.
    :raise: django.core.exceptions.ValidationError
    """
    for proc_type in procfile:
        if not PROC_TYPE_PATTERN.match(proc_type):
            raise ValidationError(f"Invalid proc type: {proc_type}, must match pattern {PROC_TYPE_PATTERN.pattern}")
        if len(proc_type) > PROC_TYPE_MAX_LENGTH:
            raise ValidationError(
                f"Invalid proc type: {proc_type}, must not longer than {PROC_TYPE_MAX_LENGTH} characters"
            )

    # Formalize procfile data and return
    return {k.lower(): v for k, v in procfile.items()}


def validate_image_repo(image_repo: str):
    """校验镜像仓库地址的主机。

    :param image_repo: 镜像仓库地址
    :raise: ValueError: 当镜像仓库地址不合法时抛出
    """
    repo_domain = parse_image(image_repo, default_registry="docker.io").domain
    try:
        host_info = parse_domain_host(repo_domain)
    except ValueError:
        raise ValueError("Invalid image repo")
    allowed_hosts = getattr(settings, "APP_IMAGE_REPO_URL_ALLOWED_HOSTS", None)

    if not match_allowed_hosts(host_info.hostname, host_info.port, allowed_hosts):
        raise ValueError(f"Invalid image repo: the host '{host_info.hostname}' is not allowed")


def validate_repo_url(repo_url: str):
    """校验源码仓库 URL 的格式、协议与主机。

    :param repo_url: 源码仓库 URL
    :raise: ValueError: 当源码仓库 URL 不合法时抛出
    """
    if repo_url.startswith("-"):
        raise ValueError("Invalid url: repo url can not start with '-'")

    host_info = parse_url_host(repo_url, SUPPORTED_REPO_URL_SCHEMES)

    allowed_hosts = getattr(settings, "APP_SOURCE_REPO_URL_ALLOWED_HOSTS", None)
    if not match_allowed_hosts(host_info.hostname, host_info.port, allowed_hosts, scheme=host_info.scheme):
        raise ValueError(f"Invalid url: the host '{host_info.hostname}' is not allowed")


def validate_safe_filename(name: str) -> str:
    """校验上传文件名是否安全，防止路径穿越。

    要求文件名：
    - 非空字符串；
    - 不为 ``.`` 或 ``..``；
    - 不包含 POSIX/Windows 路径分隔符 (``/``、``\\``)；
    - 不为绝对路径，也不会逃逸出根目录。

    校验失败时抛出 ``rest_framework.exceptions.ValidationError``。

    :param name: 待校验的文件名
    :return: 校验通过的文件名
    """

    if not isinstance(name, str) or not name:
        raise DRFValidationError(_("文件名不能为空"))

    if name in {".", ".."}:
        raise DRFValidationError(_("文件名非法"))

    if "/" in name or "\\" in name:
        raise DRFValidationError(_("文件名不能包含路径分隔符"))

    # 复用 path_may_escape 检测绝对路径和路径穿越
    if path_may_escape(name):
        raise DRFValidationError(_("文件名不能为绝对路径"))

    return name


@deconstructible
class SafeFilenameValidator:
    """DRF 自定义 FileField Validator，校验上传文件名是否安全。

    用于在 ``FileField(validators=[SafeFilenameValidator()])`` 中声明式挂载，
    从 ``UploadedFile.name`` 取出文件名后调用 ``validate_safe_filename`` 进行校验。

    :param name_pattern: 可选的文件名正则表达式，用于进一步限制文件名字符集。
        例如 ``r"[a-zA-Z0-9-_.]+"`` 只允许字母、数字、连接符、下划线和点。
    :param name_pattern_message: 正则不匹配时的错误提示信息。
    """

    def __init__(self, name_pattern: str | None = None, name_pattern_message: str = ""):
        self.name_pattern = name_pattern
        self.name_pattern_message = name_pattern_message

    def __call__(self, value):
        name = value.name
        validate_safe_filename(name)

        if self.name_pattern and not re.fullmatch(self.name_pattern, name):
            raise DRFValidationError(self.name_pattern_message)
