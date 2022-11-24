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
import random
import string
from collections import MutableMapping

from pydantic import BaseModel


def generate_password(length=10):
    """
    随机生成DB密码

    # 生成至少 大小写数字, 且包含至少一位数字的密码
    """
    password_chars = [random.choice(string.ascii_letters + string.digits) for _ in range(length)]
    password_chars.append(random.choice(string.digits))
    random.shuffle(password_chars)
    return ''.join(password_chars)


class BaseFancyModel(BaseModel, MutableMapping):
    def __getitem__(self, key):
        return getattr(self, key, None)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __delitem__(self, key):
        delattr(self, key)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)
