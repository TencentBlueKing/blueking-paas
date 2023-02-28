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

from paasng.engine.deploy.engine_svc import EngineDeployClient

pytestmark = pytest.mark.django_db


class TestEngineDeployClient:
    def test_metadata_funcs(self, bk_app, bk_stag_env):
        c = EngineDeployClient(bk_stag_env.get_engine_app())
        assert c.get_metadata()['paas_app_code'] == bk_app.code
        c.update_metadata({'paas_app_code': 'foo-updated'})
        assert c.get_metadata()['paas_app_code'] == 'foo-updated'

    def test_create_build(self, bk_stag_env):
        c = EngineDeployClient(bk_stag_env.get_engine_app())
        s = c.create_build({}, {})
        assert s is not None
