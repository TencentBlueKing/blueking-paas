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
from typing import List

from django.db import transaction
from paas_service.models import ResourceId
from paas_service.utils import Base36Handler


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


def generate_mysql_password(length: int, dictionary_words: List[str], max_attempts: int = 8) -> str:
    """
    生成符合 mysql validate_password 强密码规则的随机密码，密码长度需要大于 8
    :param length: 密码长度
    :param dictionary_words: 密码中不允许包含的常见字典词（4个字符以上）
    :param max_attempts: 最大尝试次数，默认 8 次
    """
    if length < 8:
        raise ValueError("Password length must be 8 characters or more")

    # 检查字典词是否符合要求（必须都是4个字符以上）
    for word in dictionary_words:
        if len(word) < 4:
            raise ValueError(
                f"Dictionary word '{word}' is shorter than 4 characters and does not meet the requirement"
            )

    # 检查是否超过最大尝试次数
    if max_attempts <= 0:
        raise RuntimeError("Maximum attempts reached, Failed to generate a compliant password")

    char_types = [
        # 小写字母
        string.ascii_lowercase,
        # 大写字母
        string.ascii_uppercase,
        # 数字
        string.digits,
        # 特殊字符，与腾讯云数据 MySQL 特殊字符定义保持一致
        r"""_+-,&=!@#$%^*().|""",
    ]

    # 确保每种字符类型至少有一个
    password = [random.choice(ct) for ct in char_types]

    # 生成剩余字符
    all_chars = "".join(char_types)
    remaining = max(length - len(password), 0)
    password += [random.choice(all_chars) for _ in range(remaining)]

    # 打乱顺序
    random.shuffle(password)
    password_str = "".join(password)

    # 检查是否包含字典词(4个字符以上)
    for word in dictionary_words:
        if len(word) >= 4 and word in password:
            # 如果包含字典词，重新生成
            return generate_mysql_password(length, dictionary_words, max_attempts - 1)

    return password_str
