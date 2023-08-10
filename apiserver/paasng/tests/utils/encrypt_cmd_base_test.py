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
from typing import Any, Dict, Tuple

import pytest
from blue_krill.encrypt.handler import EncryptHandler
from blue_krill.models.fields import EncryptField
from django.core.management import call_command
from django_dynamic_fixture import G

from tests.utils.helpers import generate_random_string


def generate_fernet_encrypted_instance(model_class):
    """创建一个加密模型，并生成加密字段"""

    unencryped_field_dict = {}
    instance = G(model_class)
    update_fields = []

    handler = EncryptHandler(encrypt_cipher_type='FernetCipher')

    for field in model_class._meta.fields:
        if isinstance(field, EncryptField):
            update_fields.append(field.name)

            random_str = generate_random_string()
            unencryped_field_dict[field.name] = random_str
            encryped = handler.encrypt(random_str)
            setattr(instance, field.name, encryped)

    instance.save(update_fields=update_fields)
    return instance, unencryped_field_dict


def assert_fields_encryped(pk, model_class, unencryped_field_dict, encrypt_header):
    """
    断言加密字段是否加密算法加密,且加解密成功
    :param pk: 实例主键
    :param model_class: 实例类
    :param unencryped_field_dict: 未加密字段字典
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
            assert field_value == unencryped_field_dict[field.name]


def assert_fields_encryped_with_sm4(pk, model_class, unencryped_field_dict):
    assert_fields_encryped(
        pk=pk, model_class=model_class, unencryped_field_dict=unencryped_field_dict, encrypt_header="sm4ctr$"
    )


def assert_fields_encryped_fernet(pk, model_class, unencryped_field_dict):
    assert_fields_encryped(
        pk=pk, model_class=model_class, unencryped_field_dict=unencryped_field_dict, encrypt_header="bkcrypt$"
    )


class BaseTestEnctrypMigrationCmd:
    @pytest.fixture(autouse=True)
    def generate_fernet_encrypted_instances(self, app_models):
        unencrypted_dict: Dict[Any, Tuple[Any, Dict[str, str]]] = {}

        for model_class in app_models:
            instance, unencryped_field_dict = generate_fernet_encrypted_instance(model_class)
            unencrypted_dict[model_class] = [instance.pk, unencryped_field_dict]

        return unencrypted_dict

    def test_migration_command(self, model_name, app_models, command_name, generate_fernet_encrypted_instances):
        """
        测试 migration_command
        分为两种情况:
        1、输入 model_name 参数，验证该 model 会被迁移，app 下其他的 model 不会发生迁移
        2、不输入 model_name 参数，验证该 app 下所有 model 会被迁移
        :param model_class: 实例类
        :param app_models: app 下需要考虑的 models
        :param command_name: 对应的 migration django command
        :param unencrypted_dict:未加密实例字典，存储了每个 model 的索引(pk)和
        """
        unencrypted_dict = generate_fernet_encrypted_instances
        # 验证已经被fernet算法成功加密
        for model_class in app_models:
            pk = unencrypted_dict[model_class][0]
            unencryped_field_dict = unencrypted_dict[model_class][1]
            # 验证加密算法没有迁移，并且加解密成功
            assert_fields_encryped_fernet(model_class=model_class, pk=pk, unencryped_field_dict=unencryped_field_dict)

        # 运行
        call_command(command_name, '--no-dry-run', '--model', model_name)

        for model_class in app_models:
            pk = unencrypted_dict[model_class][0]
            unencryped_field_dict = unencrypted_dict[model_class][1]
            if not model_name:
                # 验证加密算法迁移为SM4,并且加解密成功
                assert_fields_encryped_with_sm4(
                    model_class=model_class, pk=pk, unencryped_field_dict=unencryped_field_dict
                )
            elif model_class.__name__ == model_name:
                # 验证加密算法迁移为SM4,并且加解密成功
                assert_fields_encryped_with_sm4(
                    model_class=model_class, pk=pk, unencryped_field_dict=unencryped_field_dict
                )
            else:
                # 验证加密算法没有迁移，并且加解密成功
                assert_fields_encryped_fernet(
                    model_class=model_class, pk=pk, unencryped_field_dict=unencryped_field_dict
                )
