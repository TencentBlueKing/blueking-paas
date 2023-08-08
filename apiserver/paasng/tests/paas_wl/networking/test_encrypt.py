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

from paas_wl.networking.ingress.models import AppDomainSharedCert
from tests.utils.random_str import random_string

pytestmark = pytest.mark.django_db(databases=['workloads'])


class TestAppDomainSharedCert:
    def test_sm4ctr_encrypt(self):
        with connections['workloads'].cursor() as cursor:
            name = random_string(10)
            cert_data = random_string(10)
            key_data = random_string(10)
            G(AppDomainSharedCert, name=name, cert_data=cert_data, key_data=key_data)

            table_name = AppDomainSharedCert._meta.db_table
            sql = "SELECT cert_data,key_data FROM {0} WHERE name = '{1}'".format(table_name, name)
            cursor.execute(sql)
            results = cursor.fetchall()

            instance = AppDomainSharedCert.objects.get(name=name)

            assert results[0][0].startswith("sm4ctr$")
            assert results[0][1].startswith("sm4ctr$")
            assert instance.cert_data == cert_data
            assert instance.key_data == key_data

    def test_fernet_to_sm4ctr_encrypt(self):
        with connections['workloads'].cursor() as cursor:
            name = random_string(10)
            cert_data = random_string(10)
            key_data = random_string(10)
            handler = EncryptHandler('FernetCipher')
            encryped_cert_data = handler.encrypt(cert_data)
            encryped_key_data = handler.encrypt(key_data)
            G(AppDomainSharedCert, name=name, cert_data=encryped_cert_data, key_data=encryped_key_data)

            table_name = AppDomainSharedCert._meta.db_table
            sql = "SELECT cert_data,key_data FROM {0} WHERE name = '{1}'".format(table_name, name)
            cursor.execute(sql)
            results = cursor.fetchall()

            instance = AppDomainSharedCert.objects.get(name=name)

            assert results[0][0].startswith("bkcrypt$")
            assert results[0][1].startswith("bkcrypt$")
            assert instance.cert_data == cert_data
            assert instance.key_data == key_data