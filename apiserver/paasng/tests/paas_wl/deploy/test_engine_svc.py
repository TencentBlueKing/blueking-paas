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

from paas_wl.workloads.images.models import AppImageCredential
from paasng.engine.deploy.engine_svc import EngineDeployClient

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


class TestEngineDeployClient:
    def test_create_build(self, bk_stag_env, with_wl_apps):
        c = EngineDeployClient(bk_stag_env.get_engine_app())
        s = c.create_build({}, {})
        assert s is not None

    def test_update_domains(self, bk_stag_env, with_wl_apps):
        c = EngineDeployClient(bk_stag_env.get_engine_app())
        with mock.patch('paasng.engine.deploy.engine_svc.assign_custom_hosts') as mocker:
            c.update_domains(
                [
                    {'host': 'foo.example.com', 'https_enabled': True},
                    {'host': 'bar.example.com'},
                ]
            )
            assert mocker.called

    def test_update_subpaths(self, bk_stag_env, with_wl_apps):
        c = EngineDeployClient(bk_stag_env.get_engine_app())
        with mock.patch('paasng.engine.deploy.engine_svc.assign_subpaths') as mocker:
            c.update_subpaths(
                [
                    {'subpath': '/foo/'},
                    {'subpath': '/bar/'},
                ]
            )
            assert mocker.called

    def test_upsert_image_credentials(self, bk_stag_env, bk_stag_engine_app, with_wl_apps):
        c = EngineDeployClient(bk_stag_env.get_engine_app())
        with pytest.raises(AppImageCredential.DoesNotExist):
            AppImageCredential.objects.get(app=bk_stag_engine_app, registry="example.com")
        c.upsert_image_credentials('example.com', 'user', 'pass')
        assert AppImageCredential.objects.filter(app=bk_stag_engine_app).count() == 1
        assert AppImageCredential.objects.get(app=bk_stag_engine_app, registry="example.com").username == "user"
        c.upsert_image_credentials('example.com', 'user2', 'pass')
        assert AppImageCredential.objects.filter(app=bk_stag_engine_app).count() == 1
        assert AppImageCredential.objects.get(app=bk_stag_engine_app, registry="example.com").username == "user2"
