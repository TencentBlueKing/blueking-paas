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

from paasng.accounts.models import PrivateTokenHolder, Oauth2TokenHolder
from tests.utils.random_str import random_string

pytestmark = pytest.mark.django_db


class TestCommand:
    def test_conmmand_with_privatetokenholder(self):
        with connections['default'].cursor() as cursor:
            provider = random_string(10)
            private_token = random_string(10)
            handler = EncryptHandler('FernetCipher')
            encryped = handler.encrypt(private_token)
            G(PrivateTokenHolder, provider=provider, private_token=encryped)

            table_name = PrivateTokenHolder._meta.db_table
            sql = "SELECT private_token FROM {0} WHERE provider = '{1}'".format(table_name, provider)
            cursor.execute(sql)
            results = cursor.fetchall()

            call_command("encryption_migration_accounts", **{"model": "PrivateTokenHolder"})

            cursor.execute(sql)
            results_after_migrate = cursor.fetchall()

            instance = PrivateTokenHolder.objects.get(provider=provider)

            assert results[0][0].startswith("bkcrypt$")
            assert results_after_migrate[0][0].startswith("sm4ctr$")
            assert instance.private_token == private_token

    def test_conmmand_with_oauth2tokenholder(self):
        with connections['default'].cursor() as cursor:
            provider = random_string(10)
            access_token = random_string(10)
            refresh_token = random_string(10)
            handler = EncryptHandler('FernetCipher')
            encryped_access_token = handler.encrypt(access_token)
            encryped_refresh_token = handler.encrypt(refresh_token)
            G(Oauth2TokenHolder, provider=provider, access_token=encryped_access_token,
              refresh_token=encryped_refresh_token)

            table_name = Oauth2TokenHolder._meta.db_table
            sql = "SELECT access_token,refresh_token FROM {0} WHERE provider = '{1}'".format(table_name, provider)
            cursor.execute(sql)
            results = cursor.fetchall()

            call_command("encryption_migration_accounts", **{"model": "Oauth2TokenHolder"})

            cursor.execute(sql)
            results_after_migrate = cursor.fetchall()

            instance = Oauth2TokenHolder.objects.get(provider=provider)

            assert results[0][0].startswith("bkcrypt$")
            assert results[0][1].startswith("bkcrypt$")
            assert results_after_migrate[0][0].startswith("sm4ctr$")
            assert results_after_migrate[0][1].startswith("sm4ctr$")
            assert instance.access_token == access_token
            assert instance.refresh_token == refresh_token
