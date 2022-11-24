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
from django.conf import settings

from paasng.dev_resources.sourcectl.connector import ExternalGitAppRepoConnector, IntegratedSvnAppRepoConnector
from paasng.dev_resources.sourcectl.source_types import get_sourcectl_types
from paasng.utils.blobstore import detect_default_blob_store

pytestmark = pytest.mark.django_db


class TestIntegratedSvnAppRepoConnector:
    @mock.patch('paasng.dev_resources.sourcectl.connector.SvnRepositoryClient')
    def test_normal(self, mocked_client, bk_app, bk_module, init_tmpls):
        bk_module.source_init_template = settings.DUMMY_TEMPLATE_NAME

        connector = IntegratedSvnAppRepoConnector(bk_module, get_sourcectl_types().names.bk_svn)
        connector.bind("svn://svn.x.com/app/a/")
        ret = connector.sync_templated_sources(
            context={
                "region": bk_app.region,
                "owner_username": "user1",
                "app_code": bk_app.code,
                "app_secret": "nosec",
                "app_name": bk_app.name,
            }
        )
        mocked_client.assert_called()
        mocked_client().sync_dir.assert_called()

        assert ret.is_success() is True
        assert ret.dest_type == "svn"
        assert ret.extra_info["remote_source_root"] == "svn://svn.x.com/app/a/trunk"


class TestExternalGitAppRepoConnector:
    def test_normal(self, bk_app, bk_module, init_tmpls):
        bk_module.source_init_template = settings.DUMMY_TEMPLATE_NAME

        connector = ExternalGitAppRepoConnector(bk_module, "--placeholder--")
        connector.bind("git://git.x.com/some-proj.git")
        ret = connector.sync_templated_sources(
            context={
                "region": bk_app.region,
                "owner_username": "user1",
                "app_code": bk_app.code,
                "app_secret": "nosec",
                "app_name": bk_app.name,
            }
        )

        assert ret.is_success() is True
        assert ret.dest_type == detect_default_blob_store().value
        assert ret.extra_info["downloadable_address"] != ""
