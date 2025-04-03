# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import logging
from unittest import mock

import pytest
from django.test.utils import override_settings
from django.urls import reverse

from paasng.infras.bk_cmsi.client import BkNotificationService
from paasng.platform.sourcectl.models import SvnAccount
from tests.utils.basic import generate_random_string

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.django_db


@pytest.fixture()
def mocked_call_api():
    with mock.patch.object(BkNotificationService, "send_wecom") as mocked_call:
        mocked_call.return_value = True
        yield mocked_call


@pytest.fixture()
def svn_account(bk_user):
    account, _ = SvnAccount.objects.update_or_create(defaults=dict(account=generate_random_string()), user=bk_user)
    return account


class TestSvnAPI:
    def test_reset_account_error(self, mocked_call_api, api_client, bk_user, svn_account):
        data = {"verification_code": "000000"}
        with override_settings(ENABLE_VERIFICATION_CODE=True):
            response = api_client.put(
                reverse("api.sourcectl.bksvn.accounts.reset", kwargs={"id": svn_account.id}), data
            )

        assert response.status_code == 400
        assert response.json() == {
            "code": "VALIDATION_ERROR",
            "detail": "verification_code: 验证码错误",
            "fields_detail": {"verification_code": ["验证码错误"]},
        }

    def test_reset_account_skip_verification_code(self, mocked_call_api, api_client, bk_user, svn_account):
        with override_settings(ENABLE_VERIFICATION_CODE=False):
            response = api_client.put(reverse("api.sourcectl.bksvn.accounts.reset", kwargs={"id": svn_account.id}), {})

        assert response.status_code == 200
