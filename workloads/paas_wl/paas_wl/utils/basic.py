# -*- coding: utf-8 -*-
import datetime
import hashlib
from collections import MutableMapping
from typing import Collection, Dict, Tuple
from uuid import UUID

import cattr
from django.urls.resolvers import RegexPattern, URLPattern, URLResolver
from django.utils.encoding import force_bytes

# Register cattr custom hooks
cattr.register_unstructure_hook(UUID, lambda val: str(val))
cattr.register_structure_hook(UUID, lambda val, _: val if isinstance(val, UUID) else UUID(str(val)))
# End register


def get_time_delta(time_delta_string):
    """
    5m -> datetime.timedelta(minutes=5)
    5d -> datetime.timedelta(days=5)
    """
    count, _unit = time_delta_string[:-1], time_delta_string[-1]
    unit = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}.get(_unit, "minutes")
    return datetime.timedelta(**{unit: int(count)})


class AttrDict(MutableMapping):
    """Dict-like object that can be accessed by attributes"""

    def __init__(self, *args, **kwargs):
        self.__dict__.update(*args, **kwargs)

    def __getitem__(self, key):
        return self.__getattribute__(key)

    def __setitem__(self, key, val):
        self.__setattr__(key, val)

    def __delitem__(self, key):
        self.__delattr__(key)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)


def digest_if_length_exceeded(raw_str: str, limit: int):
    """如果字符串长度超长则将字符串摘要"""
    if len(raw_str) <= limit:
        return raw_str

    return hashlib.sha1(force_bytes(raw_str)).hexdigest()[:limit]


def make_subdict(d: Dict, allowed_keys: Collection):
    """Make a sub dict which includes only given keys

    :param d: original dict
    :param allowed_keys: a collections of keys
    :returns: A dict direivied from `d` but only contains `allowed_keys`
    """
    return {key: value for key, value in d.items() if key in allowed_keys}


def make_app_path(
    suffix,
    include_envs=True,
    support_envs: Tuple = ('stag', 'prod'),
    app_field_type='code',
    prefix: str = 'applications/',
) -> str:
    """Make an application URL path prefix

    :param app_field_type: app identifier type, possible values: 'code', 'uuid'
    :param prefix: default prefix of url, default to "applications/"
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
