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

import base64
import re
from typing import Dict
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_str
from moby_distribution.registry.utils import parse_image

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
        except Exception:
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
    """Validate image repo port security.

    :param image_repo: image repo
    :raise: ValueError if image repo is invalid
    """
    repo_domain = parse_image(image_repo, default_registry="docker.io").domain

    if ":" not in repo_domain:
        return

    repo_port = repo_domain.rsplit(":")[-1]

    try:
        port = int(repo_port)
    except ValueError:
        raise ValueError(f"Invalid image repo: the port {repo_port} is not an integer")

    if port in [int(p) for p in settings.FORBIDDEN_REPO_PORTS]:
        raise ValueError(f"Invalid image repo: the port number {port} is forbidden")


def validate_repo_url(repo_url: str):
    """Validate repo url format, protocol, and port security.

    :param repo_url: repo url
    :raise: ValueError if repo url is invalid
    """
    try:
        parsed_url = urlparse(repo_url)
    except Exception:
        raise ValueError("Invalid url")

    if not parsed_url.netloc:
        parsed_url = urlparse(f"https://{repo_url}")
        if not parsed_url.netloc:
            raise ValueError("Invalid url")

    if parsed_url.scheme not in ["http", "https", "git", "svn"]:
        raise ValueError("Invalid url: only support http/https/git/svn scheme")

    if parsed_url.port and parsed_url.port in [int(p) for p in settings.FORBIDDEN_REPO_PORTS]:
        raise ValueError(f"Invalid url: the port number {parsed_url.port} is forbidden")
