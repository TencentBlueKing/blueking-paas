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

# Q: 为什么需要这个包，而不是之前直接从 blue_krill 引入的方式？
# A: Python 3.11 中改变了枚举类的一些行为，且 blue_krill 不好做兼容，因此先由 apiserver 自行处理：
#    https://github.com/python/cpython/issues/100458
#    https://github.com/TencentBlueKing/bkpaas-python-sdk/issues/190

# Q: 为什么这里 import EnumField 且忽略 F401
# A: 统一枚举 import 入口，避免业务逻辑中需要从 utils.enum & blue_krill 中分别导入
from blue_krill.data_types.enum import (
    EnumField,  # noqa: F401
    StructuredEnum,
)


class StrEnum(str, StructuredEnum):
    """Py3.11+ 中替换 (str, StructuredEnum) 的枚举基类"""

    __str__ = str.__str__


class IntEnum(int, StructuredEnum):
    """Py3.11+ 中替换 (int. StructuredEnum) 的枚举基类"""

    def __str__(self):
        return "{}".format(self.value)
