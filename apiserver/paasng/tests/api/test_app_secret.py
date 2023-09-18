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
from datetime import datetime
from unittest import mock

import pytest
from django_dynamic_fixture import G
from rest_framework.reverse import reverse

from paasng.platform.oauth2.api import BkAppSecret
from paasng.platform.oauth2.models import BkAppSecretInEnvVar

pytestmark = pytest.mark.django_db


@pytest.fixture
def one_enabled_app_secret_list(bk_app):
    return [
        BkAppSecret(
            id=1,
            bk_app_code=bk_app.code,
            bk_app_secret="xxxxxxx",
            enabled=True,
            created_at=datetime.strptime('2021-10-21T07:56:16Z', "%Y-%m-%dT%H:%M:%SZ"),
        ),
    ]


@pytest.fixture
def two_enabled_app_secret_list(bk_app):
    # 默认 id 为 1 的为内置密钥
    return [
        BkAppSecret(
            id=1,
            bk_app_code=bk_app.code,
            bk_app_secret="xxxxxxx",
            enabled=True,
            created_at=datetime.strptime('2021-10-21T07:56:16Z', "%Y-%m-%dT%H:%M:%SZ"),
        ),
        BkAppSecret(
            id=2,
            bk_app_code=bk_app.code,
            bk_app_secret="xxxx",
            enabled=True,
            created_at=datetime.strptime('2022-10-21T07:56:16Z', "%Y-%m-%dT%H:%M:%SZ"),
        ),
    ]


@pytest.fixture
def change_bulitin_app_secret(bk_app):
    return G(BkAppSecretInEnvVar, bk_app_code=bk_app.code, bk_app_secret_id=2)


@pytest.fixture
def two_disabled_app_secret_list(bk_app):
    # 默认 id 为 1 的为内置密钥
    return [
        BkAppSecret(
            id=1,
            bk_app_code=bk_app.code,
            bk_app_secret="xxxxxxx",
            enabled=False,
            created_at=datetime.strptime('2021-10-21T07:56:16Z', "%Y-%m-%dT%H:%M:%SZ"),
        ),
        BkAppSecret(
            id=2,
            bk_app_code=bk_app.code,
            bk_app_secret="xxxx",
            enabled=False,
            created_at=datetime.strptime('2022-10-21T07:56:16Z', "%Y-%m-%dT%H:%M:%SZ"),
        ),
    ]


class TestAppSecret:
    @pytest.mark.parametrize(
        "has_app_permission, status_code",
        [(True, 200), (False, 403)],
    )
    def test_get_secret_perm(self, bk_app, api_client, two_enabled_app_secret_list, has_app_permission, status_code):
        with mock.patch(
            'paasng.platform.oauth2.api.BkOauthClient.get_app_secret_list',
            return_value=two_enabled_app_secret_list,
        ), mock.patch(
            "paasng.accounts.permissions.application.user_has_app_action_perm", return_value=has_app_permission
        ):

            response = api_client.get(reverse('api.bkauth.secrets', args=(bk_app.code,)))
            assert response.status_code == status_code

    @pytest.mark.parametrize(
        "has_app_permission, existing_secret_num, status_code",
        [(True, 1, 201), (True, 2, 400), (False, 1, 403), (False, 2, 403)],
    )
    def test_create_secret(
        self,
        bk_app,
        api_client,
        one_enabled_app_secret_list,
        two_enabled_app_secret_list,
        has_app_permission,
        existing_secret_num,
        status_code,
    ):
        if existing_secret_num == 1:
            return_value = one_enabled_app_secret_list
        else:
            return_value = two_enabled_app_secret_list
        with mock.patch(
            'paasng.platform.oauth2.api.BkOauthClient.get_app_secret_list',
            return_value=return_value,
        ), mock.patch('paasng.platform.oauth2.api.BkOauthClient.create_app_secret', return_value=None), mock.patch(
            "paasng.accounts.permissions.application.user_has_app_action_perm", return_value=has_app_permission
        ):
            response = api_client.post(reverse('api.bkauth.secrets', args=(bk_app.code,)))
            assert response.status_code == status_code

    @pytest.mark.parametrize(
        "has_app_permission, toggle_secret_id, status_code",
        [
            (True, 1, 400),
            (True, 2, 204),
            (False, 1, 403),
            (False, 2, 403),
        ],
    )
    def test_toggle_secret_whit_no_db_bulitin_secret(
        self, bk_app, two_enabled_app_secret_list, api_client, has_app_permission, toggle_secret_id, status_code
    ):
        with mock.patch(
            'paasng.platform.oauth2.api.BkOauthClient.get_app_secret_list', return_value=two_enabled_app_secret_list
        ), mock.patch('paasng.platform.oauth2.api.BkOauthClient.toggle_app_secret', return_value=None), mock.patch(
            "paasng.accounts.permissions.application.user_has_app_action_perm", return_value=has_app_permission
        ):
            response = api_client.post(
                reverse('api.bkauth.secret', args=(bk_app.code, toggle_secret_id)),
                data={"enabled": False},
                format='json',
            )
            assert response.status_code == status_code

    @pytest.mark.parametrize(
        "has_app_permission, toggle_secret_id, status_code",
        [(True, 1, 204), (True, 2, 400), (False, 1, 403), (False, 2, 403)],
    )
    def test_toggle_secret_whit_db_bulitin_secret(
        self,
        bk_app,
        two_enabled_app_secret_list,
        api_client,
        change_bulitin_app_secret,
        has_app_permission,
        toggle_secret_id,
        status_code,
    ):
        with mock.patch(
            'paasng.platform.oauth2.api.BkOauthClient.get_app_secret_list', return_value=two_enabled_app_secret_list
        ), mock.patch('paasng.platform.oauth2.api.BkOauthClient.toggle_app_secret', return_value=None), mock.patch(
            "paasng.accounts.permissions.application.user_has_app_action_perm", return_value=has_app_permission
        ):
            response = api_client.post(
                reverse('api.bkauth.secret', args=(bk_app.code, toggle_secret_id)),
                data={"enabled": False},
                format='json',
            )
            assert response.status_code == status_code

    @pytest.mark.parametrize(
        "has_app_permission, delete_secret_id, is_enabled, is_bulitin, status_code",
        [
            (True, 1, True, False, 400),
            (True, 1, False, True, 400),
            (False, 1, True, False, 403),
            (False, 1, False, True, 403),
        ],
    )
    def test_delete_secret(
        self,
        has_app_permission,
        bk_app,
        two_enabled_app_secret_list,
        two_disabled_app_secret_list,
        api_client,
        delete_secret_id,
        is_enabled,
        is_bulitin,
        status_code,
    ):
        if is_enabled:
            app_secret_list = two_enabled_app_secret_list
        else:
            app_secret_list = two_disabled_app_secret_list

        if is_bulitin:
            default_app_secret = two_enabled_app_secret_list[0]
        else:
            default_app_secret = two_enabled_app_secret_list[1]

        with mock.patch(
            'paasng.platform.oauth2.api.BkOauthClient.get_app_secret_list', return_value=app_secret_list
        ), mock.patch('paasng.platform.oauth2.api.BkOauthClient.del_app_secret', return_value=None), mock.patch(
            'paasng.platform.oauth2.api.BkOauthClient.get_default_app_secret', return_value=default_app_secret
        ), mock.patch(
            "paasng.accounts.permissions.application.user_has_app_action_perm", return_value=has_app_permission
        ):
            response = api_client.delete(reverse('api.bkauth.secret', args=(bk_app.code, delete_secret_id)))
            assert response.status_code == status_code

    @pytest.mark.parametrize(
        "has_app_permission, is_enabled, status_code",
        [
            (True, True, 204),
            (True, False, 400),
            (False, True, 403),
            (False, False, 403),
        ],
    )
    def test_rotate_secret(
        self,
        bk_app,
        two_enabled_app_secret_list,
        two_disabled_app_secret_list,
        api_client,
        has_app_permission,
        is_enabled,
        status_code,
    ):
        if is_enabled:
            app_secret_list = two_enabled_app_secret_list
        else:
            app_secret_list = two_disabled_app_secret_list

        with mock.patch(
            'paasng.platform.oauth2.api.BkOauthClient.get_app_secret_list', return_value=app_secret_list
        ), mock.patch(
            "paasng.accounts.permissions.application.user_has_app_action_perm", return_value=has_app_permission
        ):
            response = api_client.post(
                reverse('api.bkauth.default_secret', args=(bk_app.code,)), data={"id": 1}, format='json'
            )
            assert response.status_code == status_code
