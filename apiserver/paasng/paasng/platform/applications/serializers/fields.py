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
from typing import Optional

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import ValidationError, qs_exists

from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import get_tenant
from paasng.platform.applications.exceptions import AppFieldValidationError
from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import prepare_use_application_name
from paasng.utils.serializers import NickNameField, SafePathField
from paasng.utils.validators import RE_APP_CODE, DnsSafeNameValidator, ReservedWordValidator

from .validators import AppIDUniqueValidator


class AppIDField(serializers.RegexField):
    """Field for validating application ID"""

    def __init__(self, regex=RE_APP_CODE, *args, **kwargs):
        preset_kwargs = dict(
            max_length=16,
            min_length=3,
            required=True,
            help_text="应用 ID",
            validators=[
                ReservedWordValidator(_("应用 ID")),
                DnsSafeNameValidator(_("应用 ID")),
                AppIDUniqueValidator(),
            ],
            error_messages={
                "invalid": _("格式错误，只能包含小写字母(a-z)、数字(0-9)和半角连接符(-)，长度在 3-16 之间。")
            },
        )
        preset_kwargs.update(kwargs)
        super().__init__(regex, *args, **preset_kwargs)


class AppIDSMartField(serializers.RegexField):
    """Field for validating S-mart applications's ID, the differences to `AppIDField`:

    - max length increased from 16 to 20
    - allow using underscore("_")
    """

    # A variation of the DNS pattern with "_" allowed
    pattern = re.compile(r"^(?![0-9]+.*$)(?!-)[a-zA-Z0-9-_]{,63}(?<!-)$")

    def __init__(self, *args, **kwargs):
        preset_kwargs = dict(
            max_length=20,
            min_length=3,
            required=True,
            help_text="应用 ID",
            validators=[ReservedWordValidator(_("应用 ID")), AppIDUniqueValidator()],
            error_messages={
                "invalid": _(
                    "格式错误，只能包含小写字母(a-z)、数字(0-9)和半角连接符(-)和下划线(_)，长度在 3-20 之间。"
                )
            },
        )
        preset_kwargs.update(kwargs)
        super().__init__(self.pattern, *args, **preset_kwargs)


class ApplicationField(serializers.SlugRelatedField):
    def get_queryset(self):
        user = self.context["request"].user
        return Application.objects.filter_by_user(user=user, tenant_id=get_tenant(user).id)


class AppNameField(NickNameField):
    """Field for validating application name. It validates uniqueness within a tenant scope.

    App Tenant ID resolution (see ``_resolve_app_tenant_id``):
        Uniqueness is scoped per tenant, so ``app_tenant_id`` must be available.
        It is resolved in the following order:

        1. ``context["app_tenant_id"]`` set by the caller.
        2. The Application instance (``instance.app_tenant_id``), see ``_get_instance``.

        A ``ValidationError`` is raised if neither source provides a value.

    I18N support:
        Works with ``I18NExtend`` / ``FallbackMixin``. When used together, the
        actual i18n model field (e.g. ``name_en``, ``name_zh_cn``) is detected
        automatically for the uniqueness check. An explicit ``source`` parameter
        is also supported.
    """

    queryset = Application.default_objects.all()

    def __init__(self, *args, **kwargs):
        preset_kwargs = dict(max_length=20, help_text="应用名称")
        preset_kwargs.update(kwargs)
        super().__init__(*args, **preset_kwargs)

    def run_validators(self, value):
        super().run_validators(value)
        self._validate_unique(value)

    def _validate_unique(self, value):
        instance = self._get_instance()
        resolved_field_name = self._resolve_field_name()
        app_tenant_id = self._resolve_app_tenant_id(instance)

        qs = self.queryset.filter(**{resolved_field_name: value})
        qs = self._narrow_by_tenant(qs, app_tenant_id)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        if qs_exists(qs):
            raise ValidationError(self._get_message(resolved_field_name, value), code="unique")

        self._validate_external(value, instance=instance, field_name=resolved_field_name, app_tenant_id=app_tenant_id)

    def _get_instance(self) -> Optional[Application]:
        """Resolve the Application instance for uniqueness check.

        Resolution order:
        1. ``serializer.instance`` — silently skipped if it is a different model.
        2. ``context["application"]`` — injected by the caller for non-Application serializers.

        """
        slz_instance = getattr(self.parent, "instance", None)
        if isinstance(slz_instance, Application):
            return slz_instance

        ctx_app = self.context.get("application")
        if isinstance(ctx_app, Application):
            return ctx_app
        return None

    def _resolve_field_name(self) -> str:
        """Resolve the actual model field name for uniqueness check.

        The serializer field name may not match the model field we should check
        against. Two known scenarios:

        1. I18NExtend / FallbackMixin — ``_i18n_field_name`` carries the real
           i18n column name (e.g. "name_en", "name_zh_cn").
        2. Explicit ``source`` — e.g. ``AppNameField(source="name_en")``. If not set explicitly, source defaults to the field name when serializer is initialized.
        """
        candidates = [
            getattr(self, "_i18n_field_name", None),
            getattr(self, "source", None),
        ]
        model_meta = self.queryset.model._meta
        for candidate in candidates:
            if candidate:
                try:
                    model_meta.get_field(candidate)
                except FieldDoesNotExist:
                    pass
                else:
                    return candidate
        # fallback to "name" if no candidate is found
        return "name"

    def _resolve_app_tenant_id(self, instance: Optional[Application]) -> str:
        """Resolve ``app_tenant_id`` for the current validation.

        Resolution order:
        1. ``context["app_tenant_id"]`` set by the caller (e.g. ``AppBasicInfoMixin``).
        2. The Application instance resolved by ``_get_instance()``.

        :raises ValidationError: When none of the above provides a value.
        """
        if "app_tenant_id" in self.context:
            return self.context["app_tenant_id"]

        if instance:
            return instance.app_tenant_id

        raise ValidationError(
            "app_tenant_id is required for name uniqueness validation but was not found "
            "in serializer context, or instance."
        )

    def _narrow_by_tenant(self, queryset, app_tenant_id: str):
        """Narrow the queryset so that uniqueness is scoped per-tenant while
        also preventing conflicts with global applications.

        Rules:
        - Global apps (app_tenant_id="") must have globally unique names, so
          no filtering is applied — the queryset covers all records.
        - Tenant-specific apps must not collide with apps in the same tenant
          OR with any global app.
        """
        if app_tenant_id == "":
            return queryset

        return queryset.filter(
            Q(app_tenant_id=app_tenant_id) | Q(app_tenant_id="", app_tenant_mode=AppTenantMode.GLOBAL)
        )

    def _validate_external(self, value: str, instance: Optional[Application], field_name: str, **kwargs):
        """Send signal to external data sources for additional validation."""
        try:
            prepare_use_application_name.send(
                sender=self.__class__, value=value, instance=instance, field_name=field_name, **kwargs
            )
        except AppFieldValidationError as e:
            if e.reason == "duplicated":
                raise ValidationError(self._get_message(field_name, value), code="unique")

    def _get_message(self, field_name: str, value) -> str:
        return _("应用名称({}) 为 {} 的应用已存在").format(field_name, value)


class SourceDirField(SafePathField):
    """Field for validating source directory"""

    default_error_messages = {
        "invalid": _("构建目录 {path} 不合法"),
        "escape_risk": _("构建目录 {path} 存在逃逸风险"),
    }

    def __init__(self, **kwargs):
        preset_kwargs = dict(max_length=255, default="", allow_blank=True)
        preset_kwargs.update(kwargs)
        super().__init__(**preset_kwargs)


class DockerfilePathField(SafePathField):
    """Field for validating Dockerfile path"""

    default_error_messages = {
        "invalid": _("Dockerfile 目录 {path} 不合法"),
        "escape_risk": _("Dockerfile 目录 {path} 存在逃逸风险"),
    }

    def __init__(self, **kwargs):
        preset_kwargs = dict(max_length=255, allow_blank=True, allow_null=True)
        preset_kwargs.update(kwargs)
        super().__init__(**preset_kwargs)
