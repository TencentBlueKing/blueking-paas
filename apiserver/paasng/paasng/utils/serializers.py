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
import logging
import re
from binascii import Error as Base64DecodeError
from functools import cached_property
from typing import List, Optional, Tuple, Union

import arrow
from bkcrypto import constants as bkcrypto_constants
from bkcrypto.asymmetric import options
from bkcrypto.contrib.basic.ciphers import get_asymmetric_cipher
from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from past.builtins import basestring
from rest_framework import fields, serializers
from rest_framework.fields import empty, flatten_choices_dict, to_choices_dict

from paasng.infras.accounts.utils import get_user_avatar
from paasng.platform.sourcectl.source_types import get_sourcectl_types
from paasng.utils.datetime import convert_timestamp_to_str
from paasng.utils.file import path_may_escape
from paasng.utils.sanitizer import clean_html
from paasng.utils.validators import RE_CONFIG_VAR_KEY

logger = logging.getLogger(__name__)


class VerificationCodeField(serializers.RegexField):
    def __init__(self, **kwargs):
        kwargs.setdefault("help_text", "操作验证码")
        super(VerificationCodeField, self).__init__(regex=re.compile(r"\d{6}"), **kwargs)


class UserField(serializers.Field):
    """User field for present user friendly user object"""

    def to_representation(self, obj):
        assert isinstance(obj, basestring), "Only accept user_id"
        user = get_user_by_user_id(obj)
        avatar = get_user_avatar(user.username)
        return {"id": user.pk, "username": user.username, "provider_type": user.provider_type, "avatar": avatar}

    def to_internal_value(self, data):
        if "username" in data:
            provider_type = ProviderType(data.get("provider_type", settings.USER_TYPE))
            return user_id_encoder.encode(provider_type, data["username"])
        return data["id"]


class UserNameField(serializers.Field):
    """UserName field for present username friendly user object"""

    def to_representation(self, obj):
        assert isinstance(obj, basestring), "Only accept user_id"
        user = get_user_by_user_id(obj)
        return user.username

    def to_internal_value(self, data):
        if "username" in data:
            return user_id_encoder.encode(settings.USER_TYPE, data["username"])
        return data["id"]


class MaskField(serializers.CharField):
    """掩码字段: 只匹配符合正则规则的字符"""

    REGEX = re.compile(".")

    def to_internal_value(self, data):
        data = super().to_internal_value(data).strip()
        return "".join(self.REGEX.findall(data))


class NickNameField(MaskField):
    """
    名称字段，过滤[中文\\w\\-_]字符集
    >>> "".join(re.compile(u"[\u4300-\u9fa5\\w_\\-]+").findall(u"a中文 字母 - ——"))
    'a中文字母-'
    """

    REGEX = re.compile("[\u4e00-\u9fa5\\w\\-_]")


class ChineseField(MaskField):
    """
    中文字段
    """

    REGEX = re.compile("[\u4e00-\u9fa5" + force_str(r"\w\-\_\；\？\。\—\…\《\》\“\”\.\,\s\?\'\"\;\‘\’\r\n]"))


class RichTextField(serializers.CharField):
    """
    富文本字段，带XSS过滤供
    """

    def to_internal_value(self, data):
        data = super(RichTextField, self).to_internal_value(data)
        return clean_html(data)


class MultiUserField(serializers.CharField):
    """用于表示多个user"""

    regex = re.compile(r"(\w+[\,\;])*\w+")
    validator = RegexValidator(regex, message="用户名必须是英文,或;分隔的")
    split_regex = re.compile(r"[\,\;]")

    def to_internal_value(self, users):
        users = super(MultiUserField, self).to_internal_value(users)
        users = self.split_regex.split(users)
        users = [user.strip() for user in users if user.strip()]
        users = [user_id_encoder.encode(settings.USER_TYPE, user) for user in users]
        return users

    def to_representation(self, value):
        users = [get_user_by_user_id(user) for user in value]
        for index, user in enumerate(users):
            if not isinstance(user, basestring):
                users[index] = getattr(user, "username")
        return ",".join(users)


def patch_datetime_field():
    """Patch DateTimeField which respect current timezone
    See also: https://github.com/encode/django-rest-framework/issues/3732
    """

    def to_representation(self, value):
        # This is MAGICK!
        if value and settings.USE_TZ:
            try:
                value = timezone.localtime(value)
            except ValueError:
                pass
        return orig_to_representation(self, value)

    orig_to_representation = fields.DateTimeField.to_representation
    fields.DateTimeField.to_representation = to_representation


class HumanizeDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        return arrow.get(value).humanize(locale="zh")


class HumanizeTimestampField(serializers.Field):
    def to_representation(self, instance):
        return convert_timestamp_to_str(instance)


class Base64FileField(serializers.Field):
    """This Field wrap bytes or base64 content into File-Like Obj(using ContentFile)."""

    _prefix = "base64,"

    default_error_messages = {
        "invalid": _('"{input}" is not a valid bytes.'),
        "invalid_str": _('"{input}" is not a valid format, please startswith "base64,"'),
        "invalid_base64": _('"{input}" is not a valid base64, please check it.'),
    }

    def to_internal_value(self, data: Union[bytes, str]):
        if isinstance(data, str):
            if not data.startswith(self._prefix):
                self.fail("invalid_str", input=data)
            data = data[7:]
            try:
                data = base64.b64decode(data)
            except Exception:
                self.fail("invalid_base64", input=data)

        if not isinstance(data, bytes):
            self.fail("invalid", input=data)

        return ContentFile(data, name=self.field_name)

    def to_representation(self, value):
        if hasattr(value, "read"):
            value = value.read()

        if isinstance(value, str):
            if value.startswith(self._prefix):
                return value
            value = value.encode()

        if not isinstance(value, bytes):
            raise ValueError(f"Unsupported value: {value}")  # noqa: TRY004

        return self._prefix + (base64.b64encode(value).decode())


class SourceControlField(serializers.ChoiceField):
    """This Field provide dynamic source type choices."""

    def __init__(self, **kwargs):
        super().__init__(None, **kwargs)

    @property
    def grouped_choices(self):
        return to_choices_dict(self.choices)

    @property
    def choice_strings_to_values(self):
        return {str(key): key for key in flatten_choices_dict(self.grouped_choices)}

    def _get_choices(self):
        """always call get_choices()"""
        return dict(get_sourcectl_types().get_choices())

    def _set_choices(self, choices):
        """ignore setter"""

    def to_internal_value(self, data):
        if data == "" and self.allow_blank:
            return ""

        try:
            return self.choice_strings_to_values[str(data)]
        except KeyError:
            if self.allow_blank:
                return ""
            self.fail("invalid_choice", input=data)

    choices = property(_get_choices, _set_choices)


class ConfigVarReservedKeyValidator:
    def __init__(
        self, protected_key_list: Optional[List[str]] = None, protected_prefix_list: Optional[List[str]] = None
    ):
        self.protected_key_set = set(protected_key_list or [])
        self.protected_prefix_list = protected_prefix_list or []

    def __call__(self, value: str):
        if value in self.protected_key_set:
            raise serializers.ValidationError(f"保留关键字: {value}")
        for prefix in self.protected_prefix_list:
            if value.startswith(prefix):
                raise serializers.ValidationError(f"保留前缀: {prefix}，请尝试其他前缀")
        return value


def field_env_var_key():
    return serializers.RegexField(
        RE_CONFIG_VAR_KEY,
        max_length=1024,
        required=True,
        error_messages={"invalid": _("格式错误，只能以大写字母开头，由大写字母、数字与下划线组成。")},
        validators=[
            ConfigVarReservedKeyValidator(
                protected_key_list=getattr(settings, "CONFIGVAR_PROTECTED_NAMES", []),
                protected_prefix_list=getattr(settings, "CONFIGVAR_PROTECTED_PREFIXES", []),
            )
        ],
    )


class IntegerOrCharField(serializers.CharField):
    """整型或字符串字段，优先整型"""

    def to_internal_value(self, data):
        val = super().to_internal_value(data)
        try:
            return int(val)
        except ValueError:
            return val

    def to_representation(self, value):
        val = super().to_representation(value)
        try:
            return int(val)
        except ValueError:
            return val


class StringArrayField(fields.CharField):
    """String representation of an array field"""

    default_error_messages = {
        "max_items": _("至多包含 {max_items} 个对象."),
        "min_items": _("至少包含 {min_items} 个对象."),
    }

    def __init__(self, min_items: int | None = None, max_items: int | None = None, delimiter: str = ",", **kwargs):
        self.min_items = min_items
        self.max_items = max_items
        self.delimiter = delimiter

        super().__init__(**kwargs)

    def run_validation(self, data=empty):
        data = super().run_validation(data)

        item_cnt = len(data)
        if self.min_items is not None and item_cnt < self.min_items:
            self.fail("min_items", min_items=self.min_items)

        if self.max_items is not None and item_cnt > self.max_items:
            self.fail("max_items", max_items=self.max_items)

        return data

    def to_internal_value(self, data) -> List[str]:
        # convert string to list
        data = super().to_internal_value(data)
        return [x.strip() for x in data.split(self.delimiter) if x]


class SafePathField(serializers.RegexField):
    """安全路径字段，只允许包含字母、数字、下划线、横线、点、斜杠，不允许绝对路径 & 路径逃逸（../）"""

    regex = re.compile(r"^[a-zA-Z0-9_\-./]+$")
    default_error_messages = {
        "invalid": _("路径 {path} 不合法"),
        "escape_risk": _("路径 {path} 存在逃逸风险"),
    }

    def __init__(self, **kwargs):
        super().__init__(regex=self.regex, **kwargs)

    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, (str, int, float)):
            self.fail("invalid", path=data)
        return super().to_internal_value(data)

    def run_validation(self, data=empty):
        data = super().run_validation(data)

        # 允许空字符串 / None
        if self.allow_blank and data == "":
            return data
        if self.allow_null and data is None:
            return data

        # 检查是否使用 .. 来访问上层目录或者使用绝对路径
        if ".." in data or data.startswith("/"):
            self.fail("escape_risk", path=data)
        if path_may_escape(data):
            self.fail("escape_risk", path=data)
        return data


class BaseDecryptFieldMixin:
    """加密字段解密混入类，提供 SM2 解密能力

    支持两种输入格式:
    - 明文值: 直接传递原始字符串, 如 "the_value"
    - 加密值: 例如: {"_encrypted": true, "_encrypted_value": "xxxxx"}. "encrypted_value" 是加密后的 hex 字符串再 base64 编码
    """

    ENCRYPTED_FLAG_KEY = "_encrypted"
    ENCRYPTED_VALUE_KEY = "_encrypted_value"

    @cached_property
    def cipher_handler(self):
        if settings.FRONTEND_ENCRYPT_CIPHER_TYPE != "SM2":
            raise ImproperlyConfigured(f"unsupported cipher type: {settings.FRONTEND_ENCRYPT_CIPHER_TYPE}")

        if not (settings.FRONTEND_ENCRYPT_PUBLIC_KEY and settings.FRONTEND_ENCRYPT_PRIVATE_KEY):
            raise ImproperlyConfigured("SM2 public key or private key not set")

        return get_asymmetric_cipher(
            cipher_type=bkcrypto_constants.AsymmetricCipherType.SM2.value,
            cipher_options={
                bkcrypto_constants.AsymmetricCipherType.SM2.value: options.SM2AsymmetricOptions(
                    public_key_string=settings.FRONTEND_ENCRYPT_PUBLIC_KEY,
                    private_key_string=settings.FRONTEND_ENCRYPT_PRIVATE_KEY,
                ),
            },
        )

    def decrypt(self, value: str) -> str:
        try:
            return self.cipher_handler.decrypt(value)
        except ImproperlyConfigured:
            raise
        except Base64DecodeError:
            raise serializers.ValidationError(_("Base64 解码失败: {value}").format(value=value))
        except Exception:
            logger.exception("decrypt error")
            raise serializers.ValidationError(_("后端解密失败"))

    def is_encrypted_value(self, value) -> Tuple[bool, str]:
        """判断是否为加密值格式"""
        match value:
            case {self.ENCRYPTED_FLAG_KEY: True, self.ENCRYPTED_VALUE_KEY: val}:
                return True, val
            case {self.ENCRYPTED_FLAG_KEY: False, self.ENCRYPTED_VALUE_KEY: str()}:
                raise serializers.ValidationError(_("无效的加密值格式: {value}").format(value=value))
            case _:
                return False, value

    def decrypt_if_needed(self, value) -> str:
        """如果是加密值格式则解密，否则直接返回原始值"""
        is_encrypted, val = self.is_encrypted_value(value)
        if is_encrypted:
            return self.decrypt(val)
        return value


class DecryptableJSONField(BaseDecryptFieldMixin, serializers.JSONField):
    """
    用于接收(部分)加密的 JSON 字段, 递归处理所有值， 最大递归深度为 `self.MAX_RECURSION_DEPTH`
    加密结构约定及判断规则见 `BaseDecryptFieldMixin.is_encrypted_value`, 若为加密值会先解密
    """

    MAX_RECURSION_DEPTH = 8

    default_error_messages = {"max_recursion_depth": _("数据嵌套层级过深，最大层级为 {max_depth}")}

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return self._decrypt_recursive(data, depth=0)

    def _decrypt_recursive(self, data, depth: int):
        """递归遍历数据，解密所有加密值"""
        if depth > self.MAX_RECURSION_DEPTH:
            self.fail("max_recursion_depth", max_depth=self.MAX_RECURSION_DEPTH)

        is_encrypte, val = self.is_encrypted_value(data)
        if is_encrypte:
            return self.decrypt(val)

        if isinstance(data, dict):
            return {k: self._decrypt_recursive(v, depth + 1) for k, v in data.items()}

        if isinstance(data, list):
            return [self._decrypt_recursive(item, depth + 1) for item in data]

        return data


class DecryptableCharField(BaseDecryptFieldMixin, serializers.CharField):
    """
    用于接收可能被前端加密的字符串字段
    加密结构约定及判断规则见 `BaseDecryptFieldMixin.is_encrypted_value`, 若为加密值会先解密
    """

    def to_internal_value(self, data):
        return super().to_internal_value(self.decrypt_if_needed(data))
