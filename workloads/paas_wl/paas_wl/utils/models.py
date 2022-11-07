# -*- coding: utf-8 -*-
import re
import sys
import uuid
from typing import Callable, Dict, Optional, Type, TypeVar

import cattr
from bkpaas_auth import get_user_by_user_id
from django.conf import settings
from django.db import models
from jsonfield import JSONField
from rest_framework.exceptions import ValidationError


class AuditedModel(models.Model):
    """Audited model with 'created' and 'updated' fields."""

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UuidAuditedModel(AuditedModel):
    """Add a UUID primary key to an class`AuditedModel`."""

    uuid = models.UUIDField(
        'UUID', default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True
    )

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """Model with 'created' and 'updated' fields."""

    region = models.CharField(max_length=32, help_text="部署区域")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta(object):
        abstract = True


M = TypeVar("M")


def make_json_field(
    cls_name: str, py_model: Type[M], decoder: Callable[[M], Dict] = cattr.unstructure, module: Optional[str] = None
) -> Type[JSONField]:
    """生成会自动进行类型转换为 `py_model` 的 JSONField

    :param cls_name: 自动生成的 JSONField 的类名, 在使用时, cls_name 必须与赋值的变量名一致！否则 migrations 会报错.
    :param py_model: Python 对象, 需要能被 decoder 转换成可序列化成 json serializable 的 dict 对象.
    :param decoder: 能将 py_model instance 反序列化为 json serializable 的 dict 对象
    :param module:

    >>> @dataclass
    ... class Dummy:
    ...   foo: str
    ...   bar: bool = False
    >>> DummyField = make_json_field('DummyField', Dummy)
    """
    if not isinstance(py_model, type):
        raise NotImplementedError(f"Unsupported type: {py_model}")

    def pre_init(self, value, obj):
        """Convert a dict/list to dataclass_model object"""
        loaded_value = super(JSONField, self).pre_init(value, obj)
        if isinstance(loaded_value, py_model) or loaded_value is None:
            return loaded_value
        return cattr.structure(loaded_value, py_model)

    def get_prep_value(self, value):
        """Convert dataclass_model object to a string"""
        if isinstance(value, py_model):
            value = decoder(value)
        return super(JSONField, self).get_prep_value(value)

    def dumps_for_display(self, value):
        """Convert dataclass_model object to a string, calling by jsonfield"""
        if isinstance(value, py_model):
            return decoder(value)
        return super(JSONField, self).dumps_for_display(value)

    def to_python(self, value):
        """The jsonfield.SubfieldBase metaclass calls pre_init instead of to_python, however to_python
        is still necessary for Django's deserializer"""
        loaded_value = super(JSONField, self).to_python(value)
        if isinstance(loaded_value, py_model) or loaded_value is None:
            return loaded_value
        return cattr.structure(loaded_value, py_model)

    def from_db_value(self, value, expression, connection):
        """Convert string-like value to dataclass_model object, calling by django"""
        loaded_value = super(JSONField, self).from_db_value(value, expression, connection)
        if isinstance(loaded_value, py_model) or loaded_value is None:
            return loaded_value
        return cattr.structure(loaded_value, py_model)

    def value_to_string(self, obj):
        """Convert dataclass_model object to a string, calling by django"""
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    cls = type(
        cls_name,
        (JSONField,),
        dict(
            pre_init=pre_init,
            get_prep_value=get_prep_value,
            dumps_for_display=dumps_for_display,
            to_python=to_python,
            from_db_value=from_db_value,
            value_to_string=value_to_string,
        ),
    )

    # For pickling(and django migrations) to work, the __module__ variable needs to be set to the frame
    # where the JsonField is created.
    try:
        module = sys._getframe(1).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):
        if module is None:
            raise RuntimeError("Can't detect the module name. please provide by func args.")
    finally:
        cls.__module__ = str(module)

    assert issubclass(cls, JSONField)
    return cls


def validate_procfile(value: Dict[str, str]) -> Dict[str, str]:
    """Error if proc_type not match ^[a-z0-9]([-a-z0-9])*$"""
    for proc_type in value:
        if not re.match(settings.PROC_TYPE_PATTERN, proc_type):
            raise ValidationError(
                'Invalid proc type: %s: must match the regex %s' % (proc_type, settings.PROC_TYPE_PATTERN)
            )
    return value


class BkUserField(models.CharField):
    """Field for storing blueking user pk"""

    description = 'DB field for storing blueking user'

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 64
        kwargs['blank'] = True
        kwargs['null'] = True
        kwargs.setdefault('db_index', True)
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
