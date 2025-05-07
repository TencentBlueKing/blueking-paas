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
from collections.abc import MutableMapping

from pydantic import BaseModel


def generate_password(length=10):
    """
    随机生成DB密码

    # 生成至少 大小写数字, 且包含至少一位数字的密码
    """
    password_chars = [random.choice(string.ascii_letters + string.digits) for _ in range(length)]
    password_chars.append(random.choice(string.digits))
    random.shuffle(password_chars)
    return "".join(password_chars)


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


def gen_addons_cert_mount_path(provider_name: str, cert_name: str) -> str:
    """生成蓝鲸应用挂载增强服务 ssl 证书的路径
    重要：不要随意调整该路径，可能会导致证书无法正常挂载（需要与 ApiServer 侧同步调整）
    :param provider_name: 增强服务提供者名称，如：redis，mysql，rabbitmq（也可能与 Service 同名）
    :param cert_name: 证书名称，必须是 ca.crt，tls.crt，tls.key 三者之一
    """
    if not provider_name:
        raise ValueError("provider_name is required")

    if cert_name not in ["ca.crt", "tls.crt", "tls.key"]:
        raise ValueError("cert_name must be one of ca.crt, tls.crt, tls.key")

    return f"/opt/blueking/bkapp-addons-certs/{provider_name}/{cert_name}"
