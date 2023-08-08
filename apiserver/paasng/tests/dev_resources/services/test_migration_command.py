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
from django.core.management import call_command
from django.db import connections
from django_dynamic_fixture import G

from paasng.dev_resources.services.models import Plan, PreCreatedInstance, ServiceInstance
from tests.utils.random_str import random_string

pytestmark = pytest.mark.django_db


class TestCommand:
    def test_conmmand_with_plan(self):
        with connections['default'].cursor() as cursor:
            name = random_string(10)
            config = random_string(10)
            handler = EncryptHandler('FernetCipher')
            encryped = handler.encrypt(config)
            G(Plan, config=encryped, name=name)

            table_name = Plan._meta.db_table
            sql = "SELECT config FROM {0} WHERE name = '{1}'".format(table_name, name)
            cursor.execute(sql)
            results = cursor.fetchall()

            call_command("encryption_migration_services", model="Plan")

            cursor.execute(sql)
            results_after_migrate = cursor.fetchall()

            instance = Plan.objects.get(name=name)

            assert results[0][0].startswith("bkcrypt$")
            assert results_after_migrate[0][0].startswith("sm4ctr$")
            assert instance.config == config

    def test_conmmand_with_precreatedinstance(self):
        with connections['default'].cursor() as cursor:
            credentials = random_string(10)
            handler = EncryptHandler('FernetCipher')
            encryped = handler.encrypt(credentials)
            uuid = G(PreCreatedInstance, credentials=encryped).uuid

            table_name = PreCreatedInstance._meta.db_table
            sql = "SELECT credentials FROM {0} WHERE uuid ='{1}'".format(table_name, uuid.hex)
            cursor.execute(sql)
            results = cursor.fetchall()

            call_command("encryption_migration_services", model="PreCreatedInstance")

            cursor.execute(sql)
            results_after_migrate = cursor.fetchall()

            instance = PreCreatedInstance.objects.get(uuid=uuid)

            assert results[0][0].startswith("bkcrypt$")
            assert results_after_migrate[0][0].startswith("sm4ctr$")
            assert instance.credentials == credentials

    def test_conmmand_with_serviceinstance(self):
        with connections['default'].cursor() as cursor:
            credentials = random_string(10)
            handler = EncryptHandler('FernetCipher')
            encryped = handler.encrypt(credentials)
            uuid = G(ServiceInstance, credentials=encryped).uuid

            table_name = ServiceInstance._meta.db_table
            sql = "SELECT credentials FROM {0} WHERE uuid ='{1}'".format(table_name, uuid.hex)
            cursor.execute(sql)
            results = cursor.fetchall()

            call_command("encryption_migration_services", model="ServiceInstance")

            cursor.execute(sql)
            results_after_migrate = cursor.fetchall()

            instance = ServiceInstance.objects.get(uuid=uuid)

            assert results[0][0].startswith("bkcrypt$")
            assert results_after_migrate[0][0].startswith("sm4ctr$")
            assert instance.credentials == credentials
