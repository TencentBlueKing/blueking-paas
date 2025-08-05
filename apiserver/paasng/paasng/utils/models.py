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

# flake8: noqa
"""Utilities for django models and fields"""

import os
import sys
import uuid
import logging
from dataclasses import dataclass
from typing import Any, Optional, Type, TypeVar

import cattr
from bkpaas_auth import get_user_by_user_id
from blue_krill.encrypt.handler import EncryptHandler
from cattr._compat import is_bare as _is_bare
from cattr._compat import is_mapping as _is_mapping
from cattr._compat import is_sequence as _is_sequence
from django.core.files import File
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from django.db.models.query_utils import DeferredAttribute
from imagekit.models import ProcessedImageField as OrigProcessedImageField
from imagekit.utils import suggest_extension
from jsonfield import JSONField

from paasng.core.region.states import RegionType

logger = logging.getLogger(__name__)


def is_mapping(type: Any) -> bool:
    """判断 type 是否 mapping 类型"""
    origin = getattr(type, "__origin__", None)
    if not origin:
        return issubclass(type, dict)
    return _is_mapping(type)


def is_bare(type: Any) -> bool:
    """判断 type 是否空的 typing.Generic 类型"""
    origin = getattr(type, "__origin__", None)
    if not origin:
        return False
    return _is_bare(type)


def is_sequence(type: Any) -> bool:
    """判断 type 是否 Sequence 类型"""
    origin = getattr(type, "__origin__", None)
    if not origin:
        return issubclass(type, list)
    return _is_sequence(type)


class ImageField(models.ImageField):
    """Clone of ImageField

    Removes `storage` field in deconstruction result to avoid leaking storage info
    """

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("storage", None)
        return name, path, args, kwargs


def generate(generator, filename: str = "<memory>"):
    """
    Calls the ``generate()`` method of a generator instance, and then wraps the
    result in a Django File object so Django knows how to save it.

    Same as `imagekit.utils.generate`, but with the filename set.
    """
    content = generator.generate()
    f = File(content, name=filename)
    # The size of the File must be known or Django will try to open a file
    # without a name and raise an Exception.
    f.size = len(content.read())
    # After getting the size reset the file pointer for future reads.
    content.seek(0)
    return f


class ProcessedImageFieldFile(ImageFieldFile):
    def save(self, name, content, save=True):
        filename, ext = os.path.splitext(name)
        spec = self.field.get_spec(source=content)
        ext = suggest_extension(name, spec.format)
        new_name = "%s%s" % (filename, ext)
        content = generate(spec, filename=filename)
        return super().save(new_name, content, save)


class ProcessedImageField(OrigProcessedImageField):
    """Clone of ProcessedImageField

    Removes `storage` field in deconstruction result to avoid leaking storage info when generating
    database migration files.
    """

    attr_class = ProcessedImageFieldFile

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("storage", None)
        return name, path, args, kwargs


class BkUserFieldAttribute(DeferredAttribute):
    """A wrapper for BkUserField, always transform value to SimpleUserIDWrapper

    Example:
        class A(models.Model):
            creator = BkUserField()

        a = A.objects.create(creator=user_id_encoder.encode(ProviderType.BK, "foo"))
        assert a.creator.username == "foo"

        a.creator = user_id_encoder.encode(ProviderType.BK, "bar")
        assert a.creator.username == "bar"
    """

    def __set__(self, instance, value):
        if instance is None:
            return
        data = instance.__dict__
        field_name = self.field.attname
        if value:
            value = SimpleUserIDWrapper(value)
        data[field_name] = value


class BkUserField(models.CharField):
    """Field for storing blueking user pk"""

    description = "DB field for storing blueking user"
    descriptor_class = BkUserFieldAttribute

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 64
        kwargs["blank"] = True
        kwargs["null"] = True
        kwargs.setdefault("db_index", True)
        super(BkUserField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return SimpleUserIDWrapper(value)


class SimpleUserIDWrapper(str):
    """A simple user wrapper for convenience"""

    @property
    def username(self):
        return get_user_by_user_id(self, username_only=True).username


class TimestampedModel(models.Model):
    """Model with 'created' and 'updated' fields."""

    region = models.CharField(max_length=32, help_text="部署区域")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def get_region_display(self):
        return RegionType.get_choice_label(self.region)


class OwnerTimestampedModel(TimestampedModel):
    """Model with 'created' and 'updated' fields."""

    owner = BkUserField()

    class Meta:
        abstract = True


class WithOwnerManager(models.Manager):
    """Manager for Models with a 'owner' field"""

    @staticmethod
    def get_user_id(user):
        if hasattr(user, "pk"):
            return user.pk
        return user

    def owned_by(self, user):
        return self.get_queryset().filter(bkpaas_user_id=self.get_user_id(user))


class AuditedModel(models.Model):
    """Audited model with 'created' and 'updated' fields."""

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UuidAuditedModel(AuditedModel):
    """Add a UUID primary key to an :class:`AuditedModel`."""

    uuid = models.UUIDField(
        "UUID", default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True
    )

    class Meta:
        abstract = True


@dataclass
class OrderByField:
    """a helper class for process order_by string"""

    name: str
    is_descending: bool = False

    @classmethod
    def from_string(cls, s: str) -> "OrderByField":
        """Create an instance from string"""
        if s.startswith("-"):
            return cls(name=s[1:], is_descending=True)
        return cls(name=s)

    def __str__(self) -> str:
        """Return as string"""
        prefix = "-" if self.is_descending else ""
        return f"{prefix}{self.name}"


F = TypeVar("F", bound=models.Field)
M = TypeVar("M")


def _make_json_field(
    base_class: Type[F],
    cls_name: str,
    py_model: Type[M],
    module: Optional[str] = None,
) -> Type[F]:
    """生成会自动进行类型转换为 `py_model` 的 `base_class`

    :param base_class: 基础类型
    :param cls_name: 自动生成的 JSONField 的类名, 在使用时, cls_name 必须与赋值的变量名一致！否则 migrations 会报错.
    :param py_model: Python 模型, 需要能被 decoder 转换成可序列化成 json serializable object.
    :param module: Python 模块信息"""
    if (
        not isinstance(py_model, type)
        and not (is_sequence(py_model) and not is_bare(py_model))
        and not is_mapping(py_model)
    ):
        raise NotImplementedError(f"Unsupported type: {py_model}")

    def is_pymodel_instance(value):
        """should unstructured value to string?"""
        if is_sequence(py_model):
            elem_type = py_model.__args__[0]  # type: ignore
            return all(isinstance(v, elem_type) for v in value)
        elif is_mapping(py_model):
            return isinstance(value, dict)
        else:
            return isinstance(value, py_model)

    def pre_init(self, value, obj):
        """Convert a dict/list to `py_model` object"""
        loaded_value = base_class.pre_init(self, value, obj)
        if loaded_value is None or is_pymodel_instance(value):
            return loaded_value
        return cattr.structure(loaded_value, py_model)

    def get_prep_value(self, value):
        """Convert `py_model` object to a string"""
        # Django 4.2 中对字段转换逻辑做了调整，会导致直接
        # 传递 Cast 给到 get_prep_value，需要做特殊处理
        # ref:
        # - https://code.djangoproject.com/ticket/35167
        # - https://code.djangoproject.com/ticket/34539
        # - https://code.djangoproject.com/ticket/35381
        if hasattr(value, "as_sql"):
            return value

        if value is not None and is_pymodel_instance(value):
            value = cattr.unstructure(value)
        return base_class.get_prep_value(self, value)

    def to_python(self, value):
        """The jsonfield.SubfieldBase metaclass calls pre_init instead of to_python, however to_python
        is still necessary for Django's deserializer"""
        loaded_value = base_class.to_python(self, value)
        if loaded_value is None:
            return loaded_value
        return cattr.structure(loaded_value, py_model)

    def from_db_value(self, value, expression, connection):
        """Convert string-like value to `py_model` object, calling by django"""
        loaded_value = base_class.from_db_value(self, value, expression, connection)
        if loaded_value is None:
            return loaded_value
        return cattr.structure(loaded_value, py_model)

    def value_to_string(self, obj):
        """Convert `py_model` object to a string, calling by django"""
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    cls = type(
        cls_name,
        (base_class,),
        dict(
            pre_init=pre_init,
            get_prep_value=get_prep_value,
            to_python=to_python,
            from_db_value=from_db_value,
            value_to_string=value_to_string,
        ),
    )

    # For pickling(and django migrations) to work, the __module__ variable needs to be set to the frame
    # where the JsonField is created.
    if module is None:
        module = __get_module_from_frame()
    if module is None:
        raise RuntimeError("Can't detect the module name. please provide by func args.")
    cls.__module__ = str(module)

    assert issubclass(cls, base_class)
    return cls


def make_legacy_json_field(cls_name: str, py_model: Type[M], module: Optional[str] = None) -> Type[JSONField]:
    """生成会自动进行类型转换为 `py_model` 的 jsonfield.JSONField

    :param cls_name: 自动生成的 JSONField 的类名, 在使用时, cls_name 必须与赋值的变量名一致！否则 migrations 会报错.
    :param py_model: Python 模型, 需要能被 decoder 转换成可序列化成 json serializable object.
    :param module: Python 模块信息

    >>> @dataclass
    ... class Dummy:
    ...   foo: str
    ...   bar: bool = False
    >>> DummyField = make_legacy_json_field('DummyField', Dummy)
    """

    return _make_json_field(JSONField, cls_name, py_model, module)


def make_json_field(cls_name: str, py_model: Type[M], module: Optional[str] = None) -> Type[models.JSONField]:
    """生成会自动进行类型转换为 `py_model` 的 models.JSONField

    :param cls_name: 自动生成的 JSONField 的类名, 在使用时, cls_name 必须与赋值的变量名一致！否则 migrations 会报错.
    :param py_model: Python 模型, 需要能被 decoder 转换成可序列化成 json serializable object.
    :param module: Python 模块信息

    >>> @dataclass
    ... class Dummy:
    ...   foo: str
    ...   bar: bool = False
    >>> DummyField = make_legacy_json_field('DummyField', Dummy)
    """
    return _make_json_field(models.JSONField, cls_name, py_model, module)


def __get_module_from_frame() -> Optional[str]:
    """从函数调用堆栈中获取调用 make_json_field 的模块名"""
    try:
        # NOTE: 由于该函数在当前模块中被调用(堆栈数+1), 因此需要往上回溯 3 层堆栈.
        module = sys._getframe(3).f_globals.get("__name__", "__main__")
    except (AttributeError, ValueError):
        module = None

    return module


class RobustEncryptHandler(EncryptHandler):
    """相比原有的 EncryptHandler，在 encrypt 函数中，不再前置判断 header 是否已经存在，总是加密，
    因此调用方需要避免重复调用 encrypt 函数。

    此改动有助于解决特殊场景中可能产生的错误。用户输入本身就是包含加密标识 header 的特殊值，这导致数
    据在存储时跳过加密，数据入库后，最终在读取时触发 InvalidToken 错误。
    """

    def encrypt(self, text: str) -> str:
        """根据指定加密算法，加密字段"""
        # 根据加密类型配置选择不同的加密算法
        try:
            cipher_class = self.cipher_classes[self.encrypt_cipher_type]
        except KeyError:
            raise ValueError(f"Invalid cipher type: {self.encrypt_cipher_type}")
        else:
            cipher = cipher_class(self.secret_key)
            return cipher.encrypt(text)


class _EncryptedString(str):
    """A string that is encrypted, this type is used to distinguish between normal
    strings and encrypted ones."""


class RobustEncryptField(models.TextField):
    """相比原有的 EncryptField，有以下调整：

    - 使用 RobustEncryptHandler 作为加密处理器（encrypt 总是加密）
    - 优化 get_prep_value 函数，避免重复触发加密逻辑
    """

    description = "a field which will be encrypted"

    def __init__(self, encrypt_cipher_type: Optional[str] = None, secret_key: Optional[bytes] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = RobustEncryptHandler(encrypt_cipher_type=encrypt_cipher_type, secret_key=secret_key)

    def get_prep_value(self, value):
        if value is None:
            return value
        # 如果值已经是 EncryptedString 实例，则直接返回，避免重复触发加密逻辑
        if isinstance(value, _EncryptedString):
            return value
        return _EncryptedString(self.handler.encrypt(value))

    def get_db_prep_value(self, value, connection, prepared=False):
        return self.get_prep_value(value)

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return value
        return self.handler.decrypt(value)
