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
#
import logging
from typing import Callable, Iterable, List, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import URLPattern, URLResolver
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSetMixin

from .conf import INSURE_CHECKING_EXCLUDED_VIEWS

logger = logging.getLogger(__name__)


def ensure_views_perm_configured():
    """Check if all views have configured permissions properly.

    :raise ImproperlyConfigured: When a view function doesn't configure permission properly.
    """
    for url, view_func in list_view_funcs():
        is_admin42 = "admin42" in url

        if hasattr(view_func, "cls"):
            # A DRF style view function
            check_drf_view_perm(view_func)
        elif hasattr(view_func, "view_class"):
            # A normal Django view
            check_django_view_perm(view_func, is_admin42)
        else:
            # Function-based views
            name = view_func.__name__
            if name in INSURE_CHECKING_EXCLUDED_VIEWS:
                continue
            raise ValueError(f"Unknown view type: {view_func}")


def list_view_funcs() -> Iterable[Tuple[str, Callable]]:
    """List all view functions and url in the project."""

    def list_urls(patterns, prefix=""):
        if not patterns:
            return

        for item in patterns:
            if isinstance(item, URLPattern):
                full_url = prefix + item.pattern.regex.pattern
                yield full_url, item.callback
            elif isinstance(item, URLResolver):
                nested_prefix = prefix + item.pattern.regex.pattern
                yield from list_urls(item.url_patterns, nested_prefix)

    urlconf = __import__(settings.ROOT_URLCONF, {}, {}, [""])
    yield from list_urls(urlconf.urlpatterns)


def check_drf_view_perm(view_func):
    """Check if a DRF view function has configured permission properly.

    :raise ImproperlyConfigured: When the permission is not configured properly.
    """
    view_cls = view_func.cls
    # Skip if the view class is marked as excluded
    if view_cls.__name__ in INSURE_CHECKING_EXCLUDED_VIEWS:
        return

    if issubclass(view_cls, ViewSetMixin):
        # Some viewset doesn't configure `permission_classes`, them are protected by
        # decorators instead, make the check pass when all methods have been protected.
        unprotected_actions = get_unprotected_actions(view_func)
        if view_func.actions and not unprotected_actions:
            return
    elif issubclass(view_cls, APIView):
        # When the view class is a DRF APIView, only check the `permission_classes` property.
        pass
    else:
        raise TypeError("not a valid DRF View")

    enabled_perm = view_cls.permission_classes
    if not enabled_perm or (len(enabled_perm) == 1 and enabled_perm[0].__name__ == "IsAuthenticated"):
        name = view_cls if not unprotected_actions else f"{view_cls} - {unprotected_actions!r}"
        raise ImproperlyConfigured(
            "The view class {} has no extra permission_classes configured other than "
            "`IsAuthenticated`, this may be a bug and lead to a permission leak error, add "
            "the view name to `perm_insure.conf.INSURE_CHECKING_EXCLUDED_VIEWS` if this is intended.".format(name)
        )


def get_unprotected_actions(view_func) -> List[str]:
    """Get all unprotected actions of a DRF view function. By unprotected, it means
    the action method was not decorated by @site_perm_required or @permission_classes.
    """
    result = []
    view_cls = view_func.cls
    for action in view_func.actions.values():
        action_func = getattr(view_cls, action)
        # Skip if the {view}.{action} is marked as excluded
        name = f"{view_cls.__name__}.{action_func.__name__}"
        if name in INSURE_CHECKING_EXCLUDED_VIEWS:
            continue

        # Check if the action method were protected by @site_perm_required or
        # @permission_classes decorators.
        if not getattr(action_func, "_protected_by_site_perm_required", False) and not getattr(
            action_func, "_action_permission_classes", []
        ):
            result.append(action)
    return result


def check_django_view_perm(view_func, is_admin42: bool):
    """Check if a django view function has configured permission properly.

    :raise ImproperlyConfigured: When the permission is not configured properly.
    """
    name = view_func.view_class.__name__

    if is_admin42:
        raise ImproperlyConfigured(
            f"The view class {name} is a pure Django view, which is not supported in admin42, use DRF view instead."
        )

    if name in INSURE_CHECKING_EXCLUDED_VIEWS:
        return

    # TODO: implement the check for Django views is the future
    raise ImproperlyConfigured("Check for Django views is not implemented yet.")
