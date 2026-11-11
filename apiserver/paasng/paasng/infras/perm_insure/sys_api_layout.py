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
#
"""Check if the system APIs are organized as expected.

The system APIs are the APIs which are called by other systems, they are served under the
`sys/api/` prefix and protected by the permissions of `paasng.infras.sysapi_client`. To make
them easy to be distinguished from the user-facing APIs, they must follow the conventions
below:

1. A view class serves the `sys/api/` urls if and only if its name starts with `Sys`.
2. A view class serves the `sys/api/` urls if and only if it configures a sysapi client permission.
3. A url name starts with `sys.` if and only if it serves the `sys/api/` urls.
4. A module must not define both the `Sys` and non-`Sys` view classes.

Any violation of the conventions above produces an error by the Django system check
framework. Each rule has exactly one error id `perm_insure.E10N`, the last digit `N` is the
serial number of the rule above, e.g. `perm_insure.E103` always means the rule 3 is violated.
The two directions of a rule share the same id, they are told apart by the error message.

For the views that cannot follow the conventions, add them to `SYS_API_CHECKING_EXCLUDED_VIEWS`
in `conf.py` to skip the checking. The deprecated views which are not checked for historical
reasons are the typical cases.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable

from django.conf import settings
from django.core.checks import Error, register
from django.urls import URLPattern, URLResolver

from .conf import SYS_API_CHECKING_EXCLUDED_VIEWS, SYS_API_URL_PREFIX, SYSAPI_ROLE_MODULE


@dataclass(frozen=True)
class UrlEntry:
    """A single url entry resolved from the project's urlconf.

    :param url: The full url pattern, with the leading regex anchors stripped.
    :param name: The url name, it's empty when the route has no name.
    :param callback: The view callback, it's a DRF view function or a Django view function.
    """

    url: str
    name: str | None
    callback: Callable


def iter_url_patterns() -> Iterable[UrlEntry]:
    """Iterate over all url patterns of the project's urlconf."""

    def walk(patterns, prefix: str = ""):
        for item in patterns:
            if isinstance(item, URLPattern):
                yield prefix + item.pattern.regex.pattern, item.name, item.callback
            elif isinstance(item, URLResolver):
                yield from walk(item.url_patterns, prefix + item.pattern.regex.pattern)

    urlconf = __import__(settings.ROOT_URLCONF, {}, {}, [""])
    for url, name, callback in walk(urlconf.urlpatterns):
        # The url patterns are regular expressions, strip the anchors to make it readable.
        yield UrlEntry(url=url.lstrip("^"), name=name, callback=callback)


def is_sys_api_url(url: str) -> bool:
    """Check if the url is served under the system API prefix."""
    return url.startswith(SYS_API_URL_PREFIX)


def _split_urls(entries: list[UrlEntry]) -> tuple[list[str], list[str]]:
    """Split the urls into the system API ones and the other ones."""
    sys_urls = [entry.url for entry in entries if is_sys_api_url(entry.url)]
    other_urls = [entry.url for entry in entries if not is_sys_api_url(entry.url)]
    return sys_urls, other_urls


def get_view_class(callback: Callable) -> type | None:
    """Get the view class from a callback, return None if it's not a class based view."""
    return getattr(callback, "cls", None) or getattr(callback, "view_class", None)


def is_sys_view_cls(view_cls: type) -> bool:
    """Check if the view class is marked with the `Sys` naming prefix.

    Note that a class named "Sysfoo" is not considered as a system view, the prefix must be
    followed by an upper-cased character, e.g. "SysFooViewSet".
    """
    name = view_cls.__name__
    return name.startswith("Sys") and name[3:4].isupper()


def is_sysapi_permission(perm_cls: type) -> bool:
    """Check if the permission class is provided by the sysapi client module."""
    return getattr(perm_cls, "__module__", None) == SYSAPI_ROLE_MODULE


def _check_view_naming(view_cls: type, sys_urls: list[str], other_urls: list[str]) -> list[Error]:
    """Rule 1 (E101): the `Sys` prefix and the served urls must match each other."""
    errors = []
    if sys_urls and not is_sys_view_cls(view_cls):
        errors.append(
            Error(
                msg=(
                    f"The view class {view_cls.__name__} ({view_cls.__module__}) serves the system API url "
                    f"{sys_urls[0]!r}, but its name doesn't start with the `Sys` prefix."
                ),
                hint=(
                    "Rename the view class to `Sys<Name>` so that it can be told apart from the "
                    "user-facing views. If it's a legacy view that cannot be renamed, add it to "
                    "`perm_insure.conf.SYS_API_CHECKING_EXCLUDED_VIEWS` instead."
                ),
                id="perm_insure.E101",
            )
        )
    elif other_urls and is_sys_view_cls(view_cls):
        errors.append(
            Error(
                msg=(
                    f"The view class {view_cls.__name__} ({view_cls.__module__}) has the `Sys` prefix, "
                    f"but it serves the non system API url {other_urls[0]!r}."
                ),
                hint=(
                    "The `Sys` prefix is reserved for the views which only serve `sys/api/` urls, "
                    "split the mixed view or remove the prefix."
                ),
                id="perm_insure.E101",
            )
        )
    return errors


def _check_view_permissions(view_cls: type, sys_urls: list[str], other_urls: list[str]) -> list[Error]:
    """Rule 2 (E102): the sysapi permission and the served urls must match each other."""
    permissions = getattr(view_cls, "permission_classes", None) or []
    has_sysapi_perm = any(is_sysapi_permission(perm) for perm in permissions)

    errors = []
    if sys_urls and not has_sysapi_perm:
        errors.append(
            Error(
                msg=(
                    f"The view class {view_cls.__name__} ({view_cls.__module__}) serves the system API url "
                    f"{sys_urls[0]!r}, but it doesn't configure the sysapi client permission."
                ),
                hint=(
                    "Use `sysapi_client_perm_class()` or `sysapi_client_view_actions_perm()` to declare "
                    "which client action is required by the system API."
                ),
                id="perm_insure.E102",
            )
        )
    elif other_urls and has_sysapi_perm:
        errors.append(
            Error(
                msg=(
                    f"The view class {view_cls.__name__} ({view_cls.__module__}) configures the sysapi client "
                    f"permission, but it serves the non system API url {other_urls[0]!r}."
                ),
                hint=(
                    "The sysapi client permission only applies to the `sys/api/` urls, split the mixed "
                    "view into two view classes."
                ),
                id="perm_insure.E102",
            )
        )
    return errors


def _check_url_naming(entries: list[UrlEntry]) -> list[Error]:
    """Rule 3 (E103): the `sys.` url name prefix and the served urls must match each other."""
    errors = []
    for entry in entries:
        if not entry.name:
            continue
        is_sys_named = entry.name.startswith("sys.")
        if is_sys_api_url(entry.url) and not is_sys_named:
            errors.append(
                Error(
                    msg=(
                        f"The system API url {entry.url!r} is named {entry.name!r}, which doesn't start "
                        "with the `sys.` prefix."
                    ),
                    hint="Rename the url to `sys.api.<name-mirrors-the-path>`.",
                    id="perm_insure.E103",
                )
            )
        elif not is_sys_api_url(entry.url) and is_sys_named:
            errors.append(
                Error(
                    msg=(
                        f"The non system API url {entry.url!r} is named {entry.name!r}, which starts with "
                        "the `sys.` prefix."
                    ),
                    hint="The `sys.` prefix is reserved for the system APIs, rename the url.",
                    id="perm_insure.E103",
                )
            )
    return errors


def _check_module_layout(entries_by_view: dict[type, list[UrlEntry]]) -> list[Error]:
    """Rule 4 (E104): a module must not mix the `Sys` and non-`Sys` view classes."""
    module_views: dict[str, list[type]] = defaultdict(list)
    for view_cls in entries_by_view:
        module_views[view_cls.__module__].append(view_cls)

    errors = []
    for module_name, view_classes in sorted(module_views.items()):
        sys_classes = [cls for cls in view_classes if is_sys_view_cls(cls)]
        other_classes = [cls for cls in view_classes if not is_sys_view_cls(cls)]
        if sys_classes and other_classes:
            errors.append(
                Error(
                    msg=(
                        f"The module {module_name} defines both the system API views "
                        f"{sorted(cls.__name__ for cls in sys_classes)} and the non system API views "
                        f"{sorted(cls.__name__ for cls in other_classes)}."
                    ),
                    hint=(
                        "Move the system API views into a dedicated `sys_api.py` module (or a module whose "
                        "name ends with `_sys_api`), so that the two kinds of views are separated."
                    ),
                    id="perm_insure.E104",
                )
            )
    return errors


@register()
def check_sys_api_view_layout(app_configs, **kwargs) -> list[Error]:
    """Check if the system API views are organized as expected."""
    checked_entries: list[UrlEntry] = []
    # Group the url entries by their view class, the non class-based views are checked by
    # `check_views_perm_configured()` instead, skip them here.
    entries_by_view: dict[type, list[UrlEntry]] = defaultdict(list)
    for entry in iter_url_patterns():
        view_cls = get_view_class(entry.callback)
        if view_cls is not None and view_cls.__name__ in SYS_API_CHECKING_EXCLUDED_VIEWS:
            continue
        checked_entries.append(entry)
        if view_cls is not None:
            entries_by_view[view_cls].append(entry)

    errors = _check_url_naming(checked_entries)
    for view_cls, view_entries in entries_by_view.items():
        sys_urls, other_urls = _split_urls(view_entries)
        errors.extend(_check_view_naming(view_cls, sys_urls, other_urls))
        errors.extend(_check_view_permissions(view_cls, sys_urls, other_urls))

    errors.extend(_check_module_layout(entries_by_view))
    return errors
