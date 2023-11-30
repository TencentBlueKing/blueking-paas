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
import os
from unittest import mock

import pytest
from blue_krill.encrypt.utils import encrypt_string
from dynaconf import LazySettings

from paasng.settings.utils import (
    NAME_FOR_SIMPLE_JWT,
    get_database_conf,
    get_paas_service_jwt_clients,
    get_service_remote_endpoints,
)


@pytest.fixture()
def settings():
    return LazySettings()


def test_get_database_from_url(settings):
    db_url = "mysql://user:123456@127.0.0.0.1:3306/foo"
    with mock.patch.dict(os.environ, {"DATABASE_URL": encrypt_string(db_url)}, clear=True):
        db_conf = get_database_conf(settings)
        assert db_conf
        assert db_conf["USER"] == "user"
        assert db_conf["NAME"] == "foo"


@pytest.mark.parametrize(
    ("for_tests", "name"),
    [(False, "foo"), (True, "test_foo")],
)
def test_get_database_for_tests(settings, for_tests, name):
    settings.update({"FOO_DATABASE_PORT": 3308, "FOO_DATABASE_NAME": "foo"})
    db_conf = get_database_conf(settings, env_var_prefix="FOO_", for_tests=for_tests)
    assert db_conf
    assert db_conf["NAME"] == name
    assert db_conf["PORT"] == 3308


def test_get_paas_service_jwt_clients_simple(settings):
    settings.update({"PAAS_SERVICE_JWT_CLIENTS": None, "ONE_SIMPLE_JWT_AUTH_KEY": "foo-key"})
    assert dict(get_paas_service_jwt_clients(settings)[0]) == {
        "iss": "paas-v3",
        "key": "foo-key",
    }


def test_get_paas_service_jwt_clients_mixed(settings):
    settings.update(
        {
            "PAAS_SERVICE_JWT_CLIENTS": [{"iss": "paas-v3", "key": "bar-key"}],
            "ONE_SIMPLE_JWT_AUTH_KEY": "foo-key",
        }
    )
    assert [c["key"] for c in get_paas_service_jwt_clients(settings)] == ["bar-key", "foo-key"]


def test_get_service_remote_endpoints(settings):
    assert get_service_remote_endpoints(settings) == []

    settings.update({NAME_FOR_SIMPLE_JWT: "xus9fe15", "RSVC_BUNDLE_MYSQL_ENDPOINT_URL": "http://svc-mysql-web/"})
    assert get_service_remote_endpoints(settings)[0]["name"] == "mysql_remote"

    settings.update({"RSVC_BUNDLE_BKREPO_ENDPOINT_URL": "http://svc-bkrepo-web/"})
    assert get_service_remote_endpoints(settings)[1]["name"] == "svc_bk_repo"

    settings.update({"RSVC_BUNDLE_RABBITMQ_ENDPOINT_URL": "http://svc-rabbitmq-web/"})
    assert get_service_remote_endpoints(settings)[2]["name"] == "svc_rabbitmq"

    settings.update(
        {
            "SERVICE_REMOTE_ENDPOINTS": [
                {
                    "name": "svc_rabbitmq",
                    "endpoint_url": "http://svc-rabbitmq-web/",
                    "provision_params_tmpl": {
                        "engine_app_name": "{engine_app.name}",
                        "operator": "{engine_app.owner}",
                        "app_developers": "{app_developers}",
                    },
                    "jwt_auth_conf": {
                        "iss": "paas-v3",
                        "key": "xus9fe15",
                    },
                    "prefer_async_delete": True,
                }
            ]
        }
    )
    eps = get_service_remote_endpoints(settings)
    assert len(eps) == 1
    assert eps[0]["name"] == "svc_rabbitmq"
