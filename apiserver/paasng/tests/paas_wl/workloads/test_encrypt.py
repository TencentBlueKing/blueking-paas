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
import pytest

from blue_krill.encrypt.handler import EncryptHandler
from django.db import connections
from django_dynamic_fixture import G

from paas_wl.workloads.images.models import AppUserCredential, AppImageCredential
from tests.utils.random_str import random_string

pytestmark = pytest.mark.django_db(databases=['workloads'])


class TestAppUserCredential:
    def test_sm4ctr_encrypt(self):
        with connections['workloads'].cursor() as cursor:
            username = random_string(10)
            password = random_string(10)
            G(AppUserCredential, username=username, password=password)

            table_name = AppUserCredential._meta.db_table
            sql = "SELECT password FROM {0} WHERE username = '{1}'".format(table_name, username)
            cursor.execute(sql)
            results = cursor.fetchall()

            instance = AppUserCredential.objects.get(username=username)

            assert results[0][0].startswith("sm4ctr$")
            assert instance.password == password

    def test_fernet_to_sm4ctr_encrypt(self):
        with connections['workloads'].cursor() as cursor:
            username = random_string(10)
            password = random_string(10)
            handler = EncryptHandler('FernetCipher')
            encryped = handler.encrypt(password)
            G(AppUserCredential, username=username, password=encryped)

            table_name = AppUserCredential._meta.db_table
            sql = "SELECT password FROM {0} WHERE username = '{1}'".format(table_name, username)
            cursor.execute(sql)
            results = cursor.fetchall()

            instance = AppUserCredential.objects.get(username=username)

            assert results[0][0].startswith("bkcrypt$")
            assert instance.password == password


class TestAppImageCredential:
    def test_sm4ctr_encrypt(self):
        with connections['workloads'].cursor() as cursor:
            username = random_string(10)
            password = random_string(10)
            G(AppImageCredential, username=username, password=password)

            table_name = AppImageCredential._meta.db_table
            sql = "SELECT password FROM {0} WHERE username = '{1}'".format(table_name, username)
            cursor.execute(sql)
            results = cursor.fetchall()

            instance = AppImageCredential.objects.get(username=username)

            assert results[0][0].startswith("sm4ctr$")
            assert instance.password == password

    def test_fernet_to_sm4ctr_encrypt(self):
        with connections['workloads'].cursor() as cursor:
            username = random_string(10)
            password = random_string(10)
            handler = EncryptHandler('FernetCipher')
            encryped = handler.encrypt(password)
            G(AppImageCredential, username=username, password=encryped)

            table_name = AppImageCredential._meta.db_table
            sql = "SELECT password FROM {0} WHERE username = '{1}'".format(table_name, username)
            cursor.execute(sql)
            results = cursor.fetchall()

            instance = AppImageCredential.objects.get(username=username)

            assert results[0][0].startswith("bkcrypt$")
            assert instance.password == password
