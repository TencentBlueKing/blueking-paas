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

import logging

from cryptography.fernet import InvalidToken
from django.db import migrations, connection, transaction

from paasng.utils.models import RobustEncryptHandler

logger = logging.getLogger(__name__)


def forwards_func(apps, schema_editor):
    """加密数据库中以 bkcrypt$ 开头的环境变量值（sm4crt$ 等同样处理)

    在上一个 migration（0026）中将环境变量 value 字段从 TextField 改为 EncryptField，
    又因为目前 blue_krill 库中的加/解密函数会以 bkcrypt$ 这个前缀来判断是否为加密数据
    如果用户填写的环境变量值就是以 bkcrypt$ 开头的，那么也会被认为是加密数据（其实是明文），
    在取出进行解密的时候，会报 InvalidToken 的错误，因此本 migration 会对此类数据
    进行二次加密（本身并非特殊开头的值，由兼容性逻辑保证正常读取，因而无需处理）

    但是又存在这样一个场景：密文使用 bkpaas 的密钥进行加密，此时会无法区分是平台加密的，还是从其他地方获取的密文
    这种情况理论上不会出现，但是为了保险起见，这里还是加上了强制检查，如果出现则会抛出异常，需要运维介入处理
    """
    handler = RobustEncryptHandler()
    # 所有加密类都需要处理，可能的前缀有：bkcrypt$, sm4ctr$...
    for cipher_name, cipher_class in handler.cipher_classes.items():
        header = cipher_class.header.header
        logger.info(f"Processing cipher class {cipher_name}, header: {header}")

        with connection.cursor() as cursor:
            cursor.execute("SELECT id, value FROM engine_configvar WHERE value LIKE %s", [f"{header}%"])
            config_vars = dict(cursor.fetchall())

            for var_id, value in config_vars.items():
                try:
                    handler.decrypt(value)
                    # 确保数据库中不存在能被 bkpaas 密钥解密的数据，避免后续误将明文当做密文进行解密
                    raise ValueError(
                        f"ConfigVar (id: {var_id}) value can be decrypted by {cipher_name}."
                        + " Please delete the configuration variable or modify its value."
                    )
                except InvalidToken:
                    continue

        # 批量对数据库中的值以 header 开头的环境变量值进行加密
        with connection.cursor() as cursor:
            if update_data := [(handler.encrypt(value), var_id) for var_id, value in config_vars.items()]:
                logger.info(f"Updating {len(update_data)} config vars ({header}), ids: {list(config_vars.keys())}")
                with transaction.atomic():
                    cursor.executemany("UPDATE engine_configvar SET value = %s WHERE id = %s", update_data)


class Migration(migrations.Migration):
    dependencies = [
        ("engine", "0026_configvar_is_sensitive_alter_configvar_value_and_more"),
    ]

    operations = [migrations.RunPython(forwards_func)]
