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
from typing import Dict

from blue_krill.encrypt.handler import EncryptHandler
from blue_krill.models.fields import EncryptField
from django.core.management import call_command
from django_dynamic_fixture import G

from tests.utils.helpers import generate_random_string


def generate_fernet_encrypted_model(model_class):
    """创建一个加密模型，并生成加密字段"""

    encryped_field_dict: Dict = {}
    obj = G(model_class)
    update_fields = []

    handler = EncryptHandler(encrypt_cipher_type='FernetCipher')

    for field in model_class._meta.fields:
        if isinstance(field, EncryptField):
            update_fields.append(field.name)

            random_str = generate_random_string()
            encryped_field_dict[field.name] = random_str
            encryped = handler.encrypt(random_str)
            setattr(obj, field.name, encryped)

    obj.save(update_fields=update_fields)
    return obj, encryped_field_dict


def assert_field_encryped_with_fernet(pk, model_class):
    """
    断言加密字段是否以fernet加密算法加密
    :param pk: 实例主键
    :param model_class: 实例类
    """

    select_dict: Dict = {}
    for field in model_class._meta.fields:
        if isinstance(field, EncryptField):
            select_dict["raw_" + field.name] = field.name
    instance = model_class.objects.extra(select=select_dict).get(pk=pk)
    for field in model_class._meta.fields:
        if isinstance(field, EncryptField):
            field_value = getattr(instance, "raw_" + field.name)
            assert field_value.startswith("bkcrypt$")


def assert_encryped_with_succed(pk, model_class, encryped_field_dict, encrypt_header):
    """
    断言加密字段是否加密算法加密,且加解密成功
    :param pk: 实例主键
    :param model_class: 实例类
    :param encryped_field_dict: 加密字段字典
    """

    select_dict: Dict = {}
    for field in model_class._meta.fields:
        if isinstance(field, EncryptField):
            select_dict["raw_" + field.name] = field.name
    instance = model_class.objects.extra(select=select_dict).get(pk=pk)
    for field in model_class._meta.fields:
        if isinstance(field, EncryptField):
            field_raw_value = getattr(instance, "raw_" + field.name)
            field_value = getattr(instance, field.name)
            assert field_raw_value.startswith(encrypt_header)
            assert field_value == encryped_field_dict[field.name]


def assert_encryped_with_sm4_and_succed(pk, model_class, encryped_field_dict):
    assert_encryped_with_succed(
        pk=pk, model_class=model_class, encryped_field_dict=encryped_field_dict, encrypt_header="sm4ctr$"
    )


def assert_encryped_with_fernet_and_succed(pk, model_class, encryped_field_dict):
    assert_encryped_with_succed(
        pk=pk, model_class=model_class, encryped_field_dict=encryped_field_dict, encrypt_header="bkcrypt$"
    )


def assert_migration_command(model_name, app_models, cmd):
    """
    验证migration_command
    分为两种情况:
    1、输入model_name参数，验证该model会被迁移，app下其他的model不会发生迁移
    2、不输入model_name参数，验证该app下所有model会被迁移
    :param model_class: 实例类
    :param app_models: app下需要考虑的models
    :param cmd: 对应的migration django command
    """
    encryped_dict: Dict = {}

    for model_class in app_models:
        obj, encryped_field_dict = generate_fernet_encrypted_model(model_class)
        encryped_dict[model_class.__name__] = [obj.pk, encryped_field_dict]
        # 验证已经被fernet算法成功加密
        assert_field_encryped_with_fernet(obj.pk, model_class)

    call_command(cmd, '--no-dry-run', '--model', model_name)

    for model_class in app_models:
        pk = encryped_dict[model_class.__name__][0]
        encryped_field_dict = encryped_dict[model_class.__name__][1]
        if not model_name:
            # 验证加密算法迁移为SM4,并且加解密成功
            assert_encryped_with_sm4_and_succed(
                model_class=model_class, pk=pk, encryped_field_dict=encryped_field_dict
            )
        elif model_class.__name__ == model_name:
            # 验证加密算法迁移为SM4,并且加解密成功
            assert_encryped_with_sm4_and_succed(
                model_class=model_class, pk=pk, encryped_field_dict=encryped_field_dict
            )
        else:
            # 验证加密算法没有迁移，并且加解密成功
            assert_encryped_with_fernet_and_succed(
                model_class=model_class, pk=pk, encryped_field_dict=encryped_field_dict
            )
