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
from django.conf import settings

from paas_wl.platform.applications.models.managers import AppConfigVarManager
from paas_wl.platform.applications.models.managers.app_metadata import EngineAppMetadata
from tests.utils.app import random_fake_app

pytestmark = pytest.mark.django_db


class TestAppConfigVarManager:
    def test_app_configvar_generate(self):
        app = random_fake_app(
            force_app_info={"name": "bkapp-test_me-stag", "region": "ieod"},
            paas_app_code='test_me',
            environment='stag',
        )

        action = AppConfigVarManager(app=app)
        result = action.get_envs()
        assert result["BKPAAS_SUB_PATH"] == "/ieod-bkapp-test_me-stag/"

        result_with_process = action.get_process_envs(process_type="fake")
        assert result_with_process['BKPAAS_LOG_NAME_PREFIX'] == "ieod-bkapp-test_me-stag-fake"
        assert result_with_process['PORT'] == str(settings.CONTAINER_PORT)


class TestEngineAppMetadata:
    def test_empty_data(self):
        obj = EngineAppMetadata()
        with pytest.raises(RuntimeError):
            _ = obj.get_paas_app_code()

    def test_valid_data(self):
        obj = EngineAppMetadata(paas_app_code='foo')
        assert obj.get_paas_app_code() == 'foo'
