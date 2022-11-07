# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
import re
import subprocess
from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Tuple

from bkpaas_auth import get_user_by_user_id
from django.urls.resolvers import RegexPattern, URLPattern, URLResolver
from django.utils.encoding import force_text

if TYPE_CHECKING:
    from enum import Enum
else:
    from aenum import Enum


logger = logging.getLogger(__name__)

MOSAIC_REG = re.compile(r"(?<=\d{3})(\d{4})(?=\d{4})")


class ChoicesEnum(Enum):
    """Enum with choices"""

    _choices_labels: ClassVar[Any]

    @classmethod
    def get_choices(cls):
        # 没有设置 skip
        if isinstance(cls._choices_labels, cls):
            return cls._choices_labels.value
        return cls._choices_labels

    @classmethod
    def get_choice_label(cls, value):
        if isinstance(value, Enum):
            value = value.value
        return dict(cls.get_choices()).get(value, value)


RE_SHA256SUM = re.compile(r'[0-9a-f]{64}')


def sha256_checksum(file_path):
    """Calculate sha256sum of file"""
    possible_names = ['sha256sum', 'gsha256sum']
    for sha256_bin in possible_names:
        p = subprocess.Popen(
            '%s %s' % (sha256_bin, file_path),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
        )
        stdout, stderr = p.communicate()
        # PY3 compatibility
        stdout, stderr = force_text(stdout), force_text(stderr)
        if 'command not found' in stderr:
            continue
        else:
            searched_obj = RE_SHA256SUM.search(stdout)
            if searched_obj:
                return searched_obj.group()
    raise RuntimeError(
        ('Can not calculate sha256sum of file %s, no available command ' 'found(sha256sum|gsha256sum)') % file_path
    )


def get_username_by_bkpaas_user_id(bkpaas_user_id):
    user = get_user_by_user_id(bkpaas_user_id, username_only=True)
    return user.username


def make_app_pattern(
    suffix,
    include_envs=True,
    support_envs: Tuple = ('stag', 'prod'),
    app_field_type='code',
    prefix: str = 'api/bkapps/applications/',
) -> str:
    """Make an application URL path prefix

    :param app_field_type: app identifier type, possible values: 'code', 'uuid'
    :param prefix: default prefix of url, default to "api/bkapps/applications/"
    """
    if app_field_type == 'code':
        part_app = '(?P<code>[^/]+)'
    elif app_field_type == 'uuid':
        part_app = '(?P<application_id>[0-9a-f-]{32,36})'
    else:
        raise ValueError('Invalid app_field_type, only "code/uuid" are supported')

    if not prefix.endswith('/'):
        raise ValueError('prefix path must ends with "/"')
    part_before = f'^{prefix}{part_app}'

    part_module = r'(/modules/(?P<module_name>[^/]+))?'

    envs = "|".join(support_envs)
    part_envs = f'/envs/(?P<environment>{envs})'

    result = part_before + part_module
    if include_envs:
        result += part_envs
    return result + suffix


def make_app_pattern_with_global_envs(suffix):
    return make_app_pattern(suffix, support_envs=('stag', 'prod', '_global_'))


def get_client_ip(request):
    """获取客户端IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def desensitize_simple_str(sensitive_str):
    """给简单字符串脱敏"""
    length = len(sensitive_str)
    if length < 3:
        # 太短无法脱敏
        return sensitive_str

    start, end = length // 3, length // 3 * 2
    return "".join([sensitive_str[:start], "*" * (end - start), sensitive_str[end:]])


def first_true(iterable: Iterable, default=None) -> Any:
    """Return the first non-false item

    :param iterable: Iterable object
    :param default: The default value when no truthful value can be found
    """
    for value in iterable:
        if value:
            return value
    return default


class LegacyRegexPattern(RegexPattern):
    """This is a RegexPattern, which work like with the one in django 2.2.x

    The RegexPattern in django 3.x will no longer returns keyword arguments with ``None`` values to be passed to
    the view for the optional named groups that are missing.(In a short word, DO NOT contain the key in kwargs!)

    This duplicate will set the missing named args to None. e.g. {"named-args": None}
    """

    def match(self, path):
        match = (
            self.regex.fullmatch(path)
            if self._is_endpoint and self.regex.pattern.endswith('$')
            else self.regex.search(path)
        )
        if match:
            # If there are any named groups, use those as kwargs, ignoring
            # non-named groups. Otherwise, pass all non-named arguments as
            # positional arguments.
            kwargs = match.groupdict()
            args = () if kwargs else match.groups()
            return path[match.end() :], args, kwargs
        return None


def re_path(route, view, kwargs=None, name=None):
    """This `re_path` work like with `django.urls.re_path`,
    but will provide the missing named args as `None` instead of ignoring those."""
    if isinstance(view, (list, tuple)):
        # For include(...) processing.
        pattern = LegacyRegexPattern(route, is_endpoint=False)
        urlconf_module, app_name, namespace = view
        return URLResolver(
            pattern,
            urlconf_module,
            kwargs,
            app_name=app_name,
            namespace=namespace,
        )
    elif callable(view):
        pattern = LegacyRegexPattern(route, name=name, is_endpoint=True)
        return URLPattern(pattern, view, kwargs, name)
    else:
        raise TypeError('view must be a callable or a list/tuple in the case of include().')
