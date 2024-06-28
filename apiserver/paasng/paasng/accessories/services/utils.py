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

import random
import string
import typing
from builtins import range
from typing import Type

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from .models import ResourceId


def get_vendor_config(vendor_name: str, *, result_cls: Type):
    """Get basic config for vendor from settings"""
    all_configs = getattr(settings, "SERVICES_VENDOR_CONFIGS", {})
    try:
        value = all_configs[vendor_name]
    except KeyError:
        raise ImproperlyConfigured(
            f"No config can be found for vendor: {vendor_name}, please check `SERVICES_VENDOR_CONFIGS` settings"
        )
    return result_cls(**value)


def generate_password(length=10):
    """
    随机生成DB密码

    # 生成至少 大小写数字, 且包含至少一位数字的密码
    """
    password_chars = [random.choice(string.ascii_letters + string.digits) for _ in range(length)]
    password_chars.append(random.choice(string.digits))
    random.shuffle(password_chars)
    return "".join(password_chars)


def format_name(name):
    return name.replace("-", "_").lower()


def gen_unique_id(name: str, namespace: str = "default", max_length: int = 16, divide_char: str = "-"):
    """Generate an unique id via given name"""
    with transaction.atomic():
        # create a db instance for getting auto increment id
        resource_id = ResourceId.objects.create(namespace=namespace, uid=name)
        # use base 62 to shorten resource id
        encoded_resource_id = Base36Handler.encode(resource_id.id)

        # as default, restrict the length
        prefix = name[: max_length - len(str(encoded_resource_id)) - len(divide_char)]

        # update uid
        # example: "origin" + "-" + "aj"
        uid = prefix + divide_char + str(encoded_resource_id)
        resource_id.uid = uid
        resource_id.save(update_fields=["uid"])

    return resource_id.uid


class Base36Handler:
    # keep lowercase
    BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

    @classmethod
    def encode(cls, num: int, alphabet=BASE36):
        """Encode a positive number in Base X

        Arguments:
        - `num`: The number to encode
        - `alphabet`: The alphabet to use for encoding
        """
        if num == 0:
            return alphabet[0]
        arr = []
        base = len(alphabet)
        while num:
            num, rem = divmod(num, base)
            arr.append(alphabet[rem])
        arr.reverse()
        return "".join(arr)

    @classmethod
    def decode(cls, encoded: str, alphabet=BASE36):
        """Decode a Base X encoded string into the number

        Arguments:
        - `string`: The encoded string
        - `alphabet`: The alphabet to use for encoding
        """
        base = len(alphabet)
        str_len = len(encoded)
        num = 0

        idx = 0
        for char in encoded:
            power = str_len - (idx + 1)
            num += alphabet.index(char) * (base**power)
            idx += 1

        return num


# WR Algorithm start


class WRItem:
    """A single weighted-random items"""

    @classmethod
    def from_dict(cls, d):
        return WRItem(values=d["values"], weight=d.get("weight", 0))

    def __init__(self, values, weight=0):
        self.values = values
        self.weight = weight

    def __str__(self):
        return f"values={self.values} weight={self.weight}"


class WRItemList:
    # if the precision was set to 10, then an item which's weight is below 10% of the total weight
    # of all items is considered as zero and will never be choosed.
    precision = 100

    @classmethod
    def from_json(cls, items_list: typing.List[typing.Dict]):
        """Generate a list object from json, an example items_list:

        [
            {"values": ANY_THING, "weight": 10},
            {"values": ANY_THING, "weight": 3},
        ]
        """
        items = []
        for data in items_list:
            items.append(WRItem.from_dict(data))
        return WRItemList(items)

    def __init__(self, items: typing.List[WRItem]):
        self.items = items
        self.initalize()

    def initalize(self):
        """Caculate weight and generate a list of size 100 in order to archive the random choice"""
        total_weight = sum(item.weight for item in self.items)
        if not total_weight:
            raise ValueError("no valid items given")

        self._list_of_choices = []
        for item in self.items:
            repeats = int(self.precision * (item.weight / total_weight))
            self._list_of_choices += [item] * repeats

    def get(self) -> WRItem:
        """Pick a item based on weighted-random algorithm"""
        return random.choice(self._list_of_choices)


# WR Algorithm end
