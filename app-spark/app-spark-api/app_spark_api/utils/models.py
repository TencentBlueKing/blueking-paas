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

from typing import TYPE_CHECKING

from bkpaas_auth import get_user_by_user_id
from django.db import models
from django.db.models.query_utils import DeferredAttribute


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
        if value is not None:
            value = SimpleUserIDWrapper(value)
        data[field_name] = value


class SimpleUserIDWrapper(str):
    """A simple user wrapper for convenience"""

    __slots__ = ()

    @property
    def username(self):
        return get_user_by_user_id(self, username_only=True).username


# Django model fields are not subscriptable at runtime. Use the generic base only
# during type checking so the field can expose its actual setter and getter types.
if TYPE_CHECKING:
    _BkUserFieldBase = models.CharField[str | None, SimpleUserIDWrapper | None]
else:
    _BkUserFieldBase = models.CharField


class BkUserField(_BkUserFieldBase):
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


class TimestampedModel(models.Model):
    """Model with 'created' and 'updated' fields."""

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OwnerTimestampedModel(TimestampedModel):
    """Model with 'owner', 'created' and 'updated' fields."""

    owner = BkUserField()

    class Meta:
        abstract = True
