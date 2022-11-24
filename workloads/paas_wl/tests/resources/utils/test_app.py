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

from paas_wl.workloads.processes.managers import AppProcessManager
from tests.utils.app import random_fake_app, release_setup

pytestmark = pytest.mark.django_db


class TestProcessScheduler:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = random_fake_app(
            force_app_info={"name": "bkapp-fakeme-stag"},
            paas_app_code='fakeme',
            environment='stag',
        )
        self.release = release_setup(fake_app=self.app)

    def test_update_process_deploy_info(
        self,
    ):
        region = settings.FOR_TESTS_DEFAULT_REGION
        self.release.config.node_selector = {"non": "xxx"}
        self.release.config.tolerations = [{'key': 'key-1', 'operator': 'Equal'}]
        self.release.config.domain = "sdfsdfsdf"
        self.release.config.save()

        process = AppProcessManager(app=self.app).assemble_process(
            "web", release=self.release, extra_envs={"aaaa": "bbbb"}
        )

        assert process.schedule.node_selector == {"non": "xxx"}
        # "tolerations" should be transform to kubernetes native
        assert process.schedule.tolerations == [{'key': 'key-1', 'operator': 'Equal'}]
        assert process.runtime.envs["BKPAAS_LOG_NAME_PREFIX"] == f"{region}-bkapp-fakeme-stag-web"
        assert process.runtime.envs["aaaa"] == "bbbb"
