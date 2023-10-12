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
import copy
import logging
from contextlib import contextmanager
from unittest import mock

import pytest
from blue_krill.data_types.enum import FeatureFlagField
from django.conf import settings
from django.urls import reverse

from paasng.platform.sourcectl.models import SvnAccount
from paasng.misc.feature_flags.constants import PlatformFeatureFlag
from paasng.utils.notification_plugins import BaseComponentAPIPlugin
from tests.utils.helpers import generate_random_string

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.django_db


@pytest.fixture
def mocked_call_api():
    with mock.patch.object(BaseComponentAPIPlugin, '_call_api') as mocked_call:
        mocked_call.return_value = True
        yield mocked_call


@pytest.fixture
def svn_account(bk_user):
    account, _ = SvnAccount.objects.update_or_create(defaults=dict(account=generate_random_string()), user=bk_user)
    return account


@contextmanager
def patch_feature_flag(name, default):
    try:
        field = PlatformFeatureFlag._get_feature_fields_()[PlatformFeatureFlag(name)]
    except ValueError:
        field = FeatureFlagField(name=name, label=name, default=default)

    mocked_field = copy.deepcopy(field)
    mocked_field.default = default
    PlatformFeatureFlag.register_feature_flag(mocked_field)
    yield
    PlatformFeatureFlag.register_feature_flag(field)


class TestSvnAPI:
    @mock.patch('paasng.platform.sourcectl.svn.admin.IeodSvnAuthClient.add_user')
    def test_create_account(self, add_user, mocked_call_api, api_client, bk_user):
        def mock_add_user(account, password):
            return {"account": account.strip(), "password": password.strip()}

        add_user.side_effect = mock_add_user
        data = {'region': settings.DEFAULT_REGION_NAME}
        response = api_client.post(reverse('api.sourcectl.bksvn.accounts'), data)

        assert response.status_code == 201

    def test_reset_account_error(self, mocked_call_api, api_client, bk_user, svn_account):
        data = {'verification_code': '000000', 'region': settings.DEFAULT_REGION_NAME}
        response = api_client.put(reverse('api.sourcectl.bksvn.accounts.reset', kwargs={"id": svn_account.id}), data)

        assert response.status_code == 400
        assert response.json() == {
            'code': 'VALIDATION_ERROR',
            'detail': 'verification_code: 验证码错误',
            'fields_detail': {'verification_code': ['验证码错误']},
        }

    def test_reset_account_skip_verification_code(self, mocked_call_api, api_client, bk_user, svn_account):
        data = {'region': settings.DEFAULT_REGION_NAME}
        with patch_feature_flag(name=PlatformFeatureFlag.VERIFICATION_CODE, default=False):
            response = api_client.put(
                reverse('api.sourcectl.bksvn.accounts.reset', kwargs={"id": svn_account.id}), data
            )

        assert response.status_code == 200
