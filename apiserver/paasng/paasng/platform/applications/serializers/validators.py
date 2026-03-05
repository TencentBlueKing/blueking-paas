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

from typing import Optional

from django.core.exceptions import FieldDoesNotExist
from django.dispatch.dispatcher import Signal
from django.utils.translation import gettext_lazy as _
from rest_framework.validators import UniqueValidator, ValidationError, qs_exists

from paasng.platform.applications.exceptions import AppFieldValidationError
from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import prepare_use_application_code, prepare_use_application_name


class AppUniqueValidator(UniqueValidator):
    """Similar to the original UniqueValidator with some improvements:

    - the field_name was given directly instead of set by `set_context`
    - the error message was refined
    - an extra signal was triggered to do external check on other data sources
    """

    field_name = ""
    field_label = ""
    signal: Signal

    def __init__(self, field_name: Optional[str] = None, **kwargs):
        if field_name:
            self.field_name = field_name
        super().__init__(queryset=Application.default_objects.all(), lookup="exact", **kwargs)

    def __call__(self, value, serializer_field):
        # Determine the existing instance, if this is an update operation.
        instance = getattr(serializer_field.parent, "instance", None)
        if not isinstance(instance, Application):
            instance = serializer_field.parent.context.get("application", None)

        queryset = self.queryset
        queryset = self.filter_queryset(value, queryset, self.field_name)
        queryset = self.exclude_current_instance(queryset, instance)
        if qs_exists(queryset):
            raise ValidationError(self.get_message(value), code="unique")

        # Send signal to external data sources
        self.signal_external(value, instance=instance)

    def signal_external(self, value: str, instance: Optional[Application], **kwargs):
        """Send signal to external data sources, will raise ValidateError when external validation fails"""
        try:
            self.signal.send(sender=self.__class__, value=value, instance=instance, **kwargs)
        except AppFieldValidationError as e:
            if e.reason == "duplicated":
                raise ValidationError(self.get_message(value), code="unique")

    def get_message(self, value) -> str:
        """Get user-friendly error message"""
        return _("{} 为 {} 的应用已存在").format(_(self.field_label), value)


class AppNameUniqueValidator(AppUniqueValidator):
    """Validator for application name uniqueness.

    Extends the base validator with:
    - I18N field name resolution (name_en, name_zh_cn, etc.)
    - Tenant-scoped uniqueness (unique within the same app_tenant_id)
    """

    field_name = "name"
    field_label = "应用名称"
    signal = prepare_use_application_name

    def __call__(self, value, serializer_field):
        # Determine the existing instance, if this is an update operation.
        instance = getattr(serializer_field.parent, "instance", None)
        if not isinstance(instance, Application):
            instance = serializer_field.parent.context.get("application", None)

        field_name = self._resolve_field_name(serializer_field)
        app_tenant_id = self._resolve_app_tenant_id(serializer_field, instance)
        queryset = self.queryset
        queryset = self.filter_queryset(value, queryset, field_name)
        queryset = self._narrow_by_tenant(queryset, serializer_field, instance)
        queryset = self.exclude_current_instance(queryset, instance)
        if qs_exists(queryset):
            raise ValidationError(self.get_message(value), code="unique")

        # Send signal to external data sources
        self.signal_external(value, instance=instance, field_name=field_name, app_tenant_id=app_tenant_id)

    def _resolve_field_name(self, serializer_field) -> str:
        """Resolve the actual model field name for uniqueness check.

        The serializer field name may not match the model field we should check
        against. Two known scenarios:

        1. I18NExtend / FallbackMixin — ``_i18n_field_name`` carries the real
           i18n column name (e.g. "name_en", "name_zh_cn").
        2. Explicit ``source`` — e.g. ``AppNameField(source="name_en")``.

        We try each candidate and use the first one that maps to an actual
        model field; otherwise fall back to the class-level ``self.field_name``.
        """
        candidates = [
            getattr(serializer_field, "_i18n_field_name", None),
            getattr(serializer_field, "source", None),
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
        return self.field_name

    def _narrow_by_tenant(self, queryset, serializer_field, instance: Optional[Application]):
        """Narrow the queryset to the same ``app_tenant_id`` so that uniqueness
        is scoped per-tenant — i.e. ``(app_tenant_id, <field>)`` rather than
        global.
        """
        app_tenant_id = self._resolve_app_tenant_id(serializer_field, instance)
        return queryset.filter(app_tenant_id=app_tenant_id)

    @staticmethod
    def _resolve_app_tenant_id(serializer_field, instance: Optional[Application]) -> str:
        """Resolve ``app_tenant_id`` for the current validation.

        Resolution order:
        1. The existing ``instance`` (update operations).
        2. ``context["app_tenant_id"]`` set by the view / serializer layer.
        3. ``context["application"].app_tenant_id`` (e.g. market views).

        :raises ValidationError: When none of the above provides a value.
        """
        if instance:
            return instance.app_tenant_id

        parent = serializer_field.parent
        if parent is not None:
            context = getattr(parent, "context", {})
            if "app_tenant_id" in context:
                return context["app_tenant_id"]

            app = context.get("application")
            if isinstance(app, Application):
                return app.app_tenant_id

        raise ValidationError(
            "app_tenant_id is required for name uniqueness validation but was not found "
            "in instance, or serializer context."
        )

    def get_message(self, value) -> str:
        """Get user-friendly error message"""
        return _("{}({}) 为 {} 的应用已存在").format(_(self.field_label), self.field_name, value)


class AppIDUniqueValidator(AppUniqueValidator):
    field_name = "code"
    field_label = "应用 ID"
    signal = prepare_use_application_code

    def __call__(self, value, serializer_field):
        # Determine the existing instance, if this is an update operation.
        instance = getattr(serializer_field.parent, "instance", None)

        if not instance:
            return super().__call__(value, serializer_field)

        if instance.code != value:
            # Modifying 'code' field was forbidden at this moment
            raise ValidationError(_("不支持修改应用 ID"))
        return None
