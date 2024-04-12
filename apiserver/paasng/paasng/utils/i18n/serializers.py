# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import copy
from contextlib import ExitStack, contextmanager
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union, overload

from django.conf import settings
from django.utils.functional import Promise
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.fields import get_attribute

from paasng.utils.i18n import gettext_lazy, to_translated_field

if TYPE_CHECKING:
    _Base = Any
else:
    _Base = object


SerializerType = Type[serializers.Serializer]
DecoratorSign = Callable[[SerializerType], SerializerType]


@overload
def i18n(cls_or_languages: Optional[List[str]] = None) -> Callable[[SerializerType], SerializerType]:
    """if `cls_or_languages` is a List[str]"""


@overload
def i18n(cls_or_languages: SerializerType) -> SerializerType: ...


def i18n(
    cls_or_languages: Optional[Union[Optional[List[str]], SerializerType]] = None
) -> Union[SerializerType, Callable[[SerializerType], SerializerType]]:
    """`i18n` decorator will extend those fields wrapped by `I18NField` in the serializer."""
    languages = [lang[0] for lang in settings.LANGUAGES]
    if isinstance(cls_or_languages, list):
        languages = cls_or_languages

    def decorator(cls: Type[serializers.Serializer]) -> Type[serializers.Serializer]:
        """Find all i18n fields, add with i18n suffix, finally extend modified fields to the `_declared_fields` attr.
        And The original field will be removed.
        """
        _declared_fields = getattr(cls, "_declared_fields")  # type: Dict[str, serializers.Field]
        fields = {}
        for attr, value in cls.__dict__.items():
            if isinstance(value, I18NExtend):
                fields[attr] = value.field
        for attr, field in fields.items():
            delattr(cls, attr)
            for language_code in languages:
                i18n_field_name = to_translated_field(attr, language_code=language_code)
                _declared_fields[i18n_field_name] = copy.deepcopy(field)

        super_to_internal_value = getattr(cls, "to_internal_value")

        def to_internal_value(self, data):
            # override_field_name to the one without i18n suffix before calling to_internal_value to
            # make sure the errors will set by field_name without i18n suffix
            # ---
            # Warning: May not be compatible with all DRF versions
            # Warning: Currently affects the following logic in to_internal_value
            # - validate_method = getattr(self, 'validate_' + field.field_name, None)
            # - errors[field.field_name] = ...
            with ExitStack() as stack:
                for raw_field_name in fields.keys():
                    for language_code in languages:
                        i18n_field_name = to_translated_field(attr, language_code=language_code)

                        stack.enter_context(self.fields[i18n_field_name].override_field_name(raw_field_name))
                return super_to_internal_value(self, data)

        setattr(cls, "to_internal_value", to_internal_value)
        return cls

    if cls_or_languages is None:
        return decorator
    elif isinstance(cls_or_languages, type) and issubclass(cls_or_languages, serializers.Serializer):
        return decorator(cls_or_languages)
    raise NotImplementedError


class I18NExtend:
    """i18n extend flag for drf Serializer class.
    This field should be used at **incoming** field in the Serializer and muse use with the `i18n` decorator.

    Generally, this field will inject other field(named by i18n rule) to the Serializer class which decorate with i18n
    For Example, we have some incoming data look like:
    >>> data = {"field_en": "alpha", "field_zh_cn": "阿尔法"}

    Then we can defind a Serializer with I18NField(and i18n decorator):
    >>> @i18n
    ... class DataSLZ(serializers.Serializer):
    ...     field = I18NExtend(serializers.CharField())
    ...
    ... slz = DataSLZ(data={"field_en": "alpha", "field_zh_cn": "阿尔法"})
    ... slz.is_valid(raise_exception=True)
    ... assert slz.validated_data == {"field_en": "alpha", "field_zh_cn": "阿尔法"}
    """

    def __init__(self, base_field: serializers.Field, **kwargs) -> None:
        # languages: What languages does this Field support
        self.languages = list(kwargs.pop("languages", (lang[0] for lang in settings.LANGUAGES)))
        assert base_field.source is None, (
            "The `source` argument is not meaningful for I18NField." "Remove `source=` from the field declaration."
        )
        self.kwargs = kwargs
        self._base_field = base_field

    def __set_name__(self, owner, name):
        self._fallback_field_name = name

    @property
    def field(self):
        return type("FallbackField", (FallbackMixin, type(self._base_field)), {})(
            fallback_field_name=self._fallback_field_name, **self._base_field._kwargs
        )


class TranslatedCharField(serializers.CharField):
    """A CharField supported i18n, which will work with django translation rule.
    This field can be used at **incoming** or **outgoing** field in the Serializer.

    For instance, assume that the fields of the data follow the rule as follow:
    >>> class Dummy:
    ... field_en: str
    ... field_zh_cn: str

    For the example data above, we can defind a Serializer with `TranslatedCharField`
    to auto return the `field` translated.

    When using at **incoming** field,
    TranslatedCharField will colllect mulit fields are named with i18n suffix from `data`
    and return only one field according to the request language. For Example:

    >>> class DummySLZ(serializers.Serializer):
    ...     field = TranslatedCharField()
    ... slz = DummySLZ(data={"field_en": "alpha", "field_zh_cn": "阿尔法"})
    ... slz.is_valid(raise_exception=True)
    ... assert slz.validated_data == {"field": "阿尔法"}

    When using at **outgoing** field,
    TranslatedCharField will collect multi fields are named with i18n suffix from `instnace`,
    and return only one field according to the request language. For Example:

    >>> class DummySLZ(serializers.Serializer):
    ...     field = TranslatedCharField()
    ... slz = DummySLZ(instance={"field_en": "alpha", "field_zh_cn": "阿尔法"})
    ... assert slz.data == {"field": "阿尔法"}
    """

    def __init__(self, **kwargs):
        # languages: What languages does this Field support
        self.languages = list(kwargs.pop("languages", (lang[0] for lang in settings.LANGUAGES)))
        super().__init__(**kwargs)

    def get_attribute(self, instance) -> Union[str, Promise]:
        """This function will return a lazy proxy, which will pick up the translation dynamically."""
        values = {}
        for language_code in self.languages:
            i18n_field_name = to_translated_field(self.field_name, language_code=language_code)
            try:
                _value = get_attribute(instance, [i18n_field_name])
                values[language_code] = str(_value) if _value is not None else ""
                if values[language_code] == "" and not self.allow_blank and _value is not None:
                    values[language_code] = str(super().get_attribute(instance))
            except (KeyError, AttributeError):
                values[language_code] = str(super().get_attribute(instance))
        return gettext_lazy(values)

    def get_value(self, dictionary) -> Dict[str, str]:
        """Return a Dict, which take the language code as the key and the translation result as the value"""
        values = {}
        for language_code in self.languages:
            i18n_field_name = to_translated_field(self.field_name, language_code=language_code)
            values[i18n_field_name] = dictionary.get(
                i18n_field_name, dictionary.get(self.field_name, serializers.empty)
            )
        return values

    def run_validation(self, data=serializers.empty) -> Union[str, Promise]:
        """Usually, `run_validation` will be called after `get_value` function called.
        And the `data` will be a Dict got by the `get_value` function.
        This function will return a lazy proxy, which will pick up the translation dynamically.

        :param data:
        :return:
        """
        if not isinstance(data, dict):
            value = super().run_validation(data)
            return value

        for language_code in self.languages:
            i18n_field_name = to_translated_field(self.field_name, language_code=language_code)
            value = data.pop(i18n_field_name, serializers.empty)
            if value == '' or (self.trim_whitespace and str(value).strip() == ''):
                if not self.allow_blank:
                    self.fail('blank')
                value = ''
            value = super().run_validation(value)
            data[language_code] = str(value)
        return gettext_lazy(data)


class FallbackMixin(_Base):
    """A Mixin for drf.Field
    which will get value/attribute from `fallback_field_name` when we can't get value/attribute from `i18n_field_name`
    """

    # origin field_name of drf.Field, will be used to initialize ValidationError
    field_name: str
    # the field_name with i18n suffix, e.g. name_zh_cn
    _i18n_field_name: str
    # the field_name without i18n suffix, e.g. name
    _fallback_field_name: str

    def __init__(self, **kwargs):
        self._fallback_field_name = kwargs.pop("fallback_field_name", None)
        # _i18n_field_name is set up by `.bind()` when the field is added to a serializer.
        self._i18n_field_name = None  # type: ignore
        source = kwargs.pop("source", None)
        assert source is None, (
            "The `source` argument is not meaningful FallbackCharField." "Remove `source=` from the field declaration."
        )
        super().__init__(**kwargs)

    def bind(self, field_name: str, parent):
        """
        Initializes the field name and parent for the field instance.
        Called when a field is added to the parent serializer instance.
        """
        # bind _fallback_field_name to origin field_name, because field_name will be used to initialize ValidationError
        super().bind(field_name=field_name, parent=parent)
        # set _i18n_field_name
        self._i18n_field_name = field_name
        # self.source should default to being the same as the field name.
        self.source = field_name
        # self.source_attrs is a list of attributes that need to be looked up
        # when serializing the instance, or populating the validated data.
        self.source_attrs = self.source.split('.')

    def get_value(self, dictionary):
        """
        Given the *incoming* primitive data, return the value for this field
        that should be validated and transformed to a native value.

        get_value is using `field_name` to get value from dictionary
        """
        with self.override_field_name(self._i18n_field_name):
            value = super().get_value(dictionary)
        if value is serializers.empty:
            with self.override_field_name(self._fallback_field_name):
                value = super().get_value(dictionary)
        return value

    def get_attribute(self, instance):
        """
        Given the *outgoing* object instance, return the primitive value
        that should be used for this field.

        get_attribute is using `source_attrs` to get attribute from instance
        """
        try:
            with self.override_field_name(self._i18n_field_name, override_source_attrs=True):
                return super().get_attribute(instance)
        except (KeyError, AttributeError):
            with self.override_field_name(self._fallback_field_name, override_source_attrs=True):
                return super().get_attribute(instance)

    @contextmanager
    def override_field_name(self, field_name: str, override_source: bool = False, override_source_attrs: bool = False):
        cache = self.field_name, self.source, self.source_attrs
        try:
            self.field_name = field_name
            if override_source:
                self.source = field_name
            if override_source_attrs:
                self.source_attrs = field_name.split(".")
            yield
        finally:
            self.field_name, self.source, self.source_attrs = cache


class DjangoTranslatedCharField(serializers.CharField):
    """Translate strings using django gettext method"""

    def to_representation(self, value):
        return _(super().to_representation(value))
