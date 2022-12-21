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
from unittest import mock

import pytest
from blue_krill.contextlib import nullcontext as does_not_raise
from django.conf import settings
from django.test.utils import override_settings

from paasng.platform.oauth2.exceptions import BkOauthApiException
from paasng.platform.oauth2.models import OAuth2Client
from paasng.platform.oauth2.utils import create_oauth2_client, get_oauth2_client_secret

pytestmark = pytest.mark.django_db


@mock.patch("paasng.platform.oauth2.api.BkOauthClient")
class TestBkOauthClient:
    @pytest.mark.parametrize(
        "enable_bk_oauth, ctx", [(True, pytest.raises(BkOauthApiException)), (False, does_not_raise())]
    )
    def test_create_client(self, BkOauthClient, bk_oauth_client_id, bk_oauth_client_key, enable_bk_oauth, ctx):
        BkOauthClient().get_client_secret.return_value = bk_oauth_client_key
        settings.ENABLE_BK_OAUTH = enable_bk_oauth

        with override_settings(ENABLE_BK_OAUTH=enable_bk_oauth):
            region = "default"
            with ctx:
                create_oauth2_client(bk_oauth_client_id, region)
                client_secret = get_oauth2_client_secret(bk_oauth_client_id, region)
                if enable_bk_oauth:
                    assert client_secret == bk_oauth_client_key
                else:
                    client_secret_in_db = OAuth2Client.objects.get(client_id=bk_oauth_client_id).client_secret
                    assert client_secret == client_secret_in_db
