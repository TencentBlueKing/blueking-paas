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
from datetime import datetime
from unittest import mock

import pytest

from paasng.infras.oauth2.api import BkAppSecret
from paasng.infras.oauth2.utils import create_oauth2_client, get_oauth2_client_secret

pytestmark = pytest.mark.django_db


class TestBkOauthClient:
    def test_create_client(self, bk_oauth_client_id, bk_oauth_client_key):
        secret_obj = BkAppSecret(
            id=1,
            bk_app_code=bk_oauth_client_id,
            bk_app_secret=bk_oauth_client_key,
            enabled=True,
            created_at=datetime.strptime("2021-10-21T07:56:16Z", "%Y-%m-%dT%H:%M:%SZ"),
        )

        with mock.patch("paasng.infras.oauth2.utils.get_app_secret_in_env_var", return_value=secret_obj), mock.patch(
            "paasng.infras.oauth2.utils.create_oauth2_client", return_value=secret_obj
        ):
            create_oauth2_client(bk_oauth_client_id)
            client_secret = get_oauth2_client_secret(bk_oauth_client_id)
            assert client_secret == bk_oauth_client_key
