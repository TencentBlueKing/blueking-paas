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
    """加密数据库中以 bkcrypt$ 开头的环境变量值"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, value FROM engine_configvar WHERE value LIKE %s", ("bkcrypt$%",))
        config_vars = dict(cursor.fetchall())
        handler = RobustEncryptHandler()

        for var_id, value in config_vars.items():
            try:
                handler.decrypt(value)
                # 确保数据库中不存在能被 bkpaas 密钥解密的数据，避免后续误将明文当做密文进行解密
                raise ValueError(f"Invalid ConfigVar (id: {var_id}) value can be decrypted with bkpaas secret")
            except InvalidToken:
                continue

        # 批量对数据库中的值以 bkcrypt$ 开头的环境变量值进行加密
        if update_data := [(handler.encrypt(value), var_id) for var_id, value in config_vars.items()]:
            with transaction.atomic():
                cursor.executemany("UPDATE engine_configvar SET value = %s WHERE id = %s", update_data)


class Migration(migrations.Migration):
    dependencies = [
        ("engine", "0026_configvar_is_sensitive_alter_configvar_value_and_more"),
    ]

    operations = [migrations.RunPython(forwards_func)]
