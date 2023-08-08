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

from paasng.platform.oauth2.models import OAuth2Client
from tests.utils.random_str import random_string

pytestmark = pytest.mark.django_db


class TestCommand:
    def test_conmmand_with_oauth2client(self):
        with connections['default'].cursor() as cursor:
            client_id = random_string(10)
            client_secret = random_string(10)
            handler = EncryptHandler('FernetCipher')
            encryped = handler.encrypt(client_secret)
            G(OAuth2Client, client_id=client_id, client_secret=encryped)

            table_name = OAuth2Client._meta.db_table
            sql = "SELECT client_secret FROM {0} WHERE client_id = '{1}'".format(table_name, client_id)
            cursor.execute(sql)
            results = cursor.fetchall()

            call_command("encryption_migration_oauth2", **{"model": "OAuth2Client"})

            cursor.execute(sql)
            results_after_migrate = cursor.fetchall()

            instance = OAuth2Client.objects.get(client_id=client_id)

            assert results[0][0].startswith("bkcrypt$")
            assert results_after_migrate[0][0].startswith("sm4ctr$")
            assert instance.client_secret == client_secret
