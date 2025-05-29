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

from unittest import mock

import pytest
from django.conf import settings

from paasng.platform.sourcectl.connector import ExternalGitAppRepoConnector, IntegratedSvnAppRepoConnector
from paasng.platform.sourcectl.source_types import get_sourcectl_types
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.utils.blobstore import detect_default_blob_store

pytestmark = pytest.mark.django_db


class TestIntegratedSvnAppRepoConnector:
    @pytest.mark.usefixtures("_init_tmpls")
    @mock.patch("paasng.platform.sourcectl.connector.SvnRepositoryClient")
    def test_normal(self, mocked_client, bk_app, bk_module):
        bk_module.source_init_template = settings.DUMMY_TEMPLATE_NAME

        connector = IntegratedSvnAppRepoConnector(bk_module, get_sourcectl_types().names.bk_svn)
        repo_url = "svn://svn.x.com/app/a/"
        connector.bind(repo_url)

        template = Template.objects.get(name=settings.DUMMY_TEMPLATE_NAME)
        connector.init_repo(
            template,
            repo_url,
            context={
                "region": bk_app.region,
                "owner_username": "user1",
                "app_code": bk_app.code,
                "app_secret": "nosec",
                "app_name": bk_app.name,
            },
        )
        mocked_client.assert_called()
        mocked_client().sync_dir.assert_called()


class TestExternalGitAppRepoConnector:
    @pytest.mark.usefixtures("_init_tmpls")
    def test_normal(self, bk_app, bk_module):
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
            },
        )

        assert ret.is_success() is True
        assert ret.dest_type == detect_default_blob_store().value
        assert ret.extra_info["downloadable_address"] != ""

    @pytest.mark.usefixtures("_init_tmpls")
    @mock.patch("paasng.platform.sourcectl.connector.ExternalGitAppRepoConnector._fix_git_user_config")
    @mock.patch("paasng.platform.sourcectl.connector.ExternalGitAppRepoConnector.client")
    def test_init_repo_normal(self, mocked_client, mock_fix_config, bk_app, bk_module):
        """测试正常初始化代码仓库"""
        # mock 模板对象
        mock_template = mock.Mock()
        mock_template.name = settings.DUMMY_TEMPLATE_NAME
        mock_template.type = TemplateType.NORMAL

        # mock GitClient 方法
        mocked_client.return_value.clone.return_value = None
        mocked_client.return_value.add.return_value = None
        mocked_client.return_value.commit.return_value = None
        mocked_client.return_value.push.return_value = None

        connector = ExternalGitAppRepoConnector(bk_module, "tc_git")
        connector.init_repo(
            template=mock_template,
            repo_url="http://git.example.com/test-group/repo1.git",
            context={
                "region": bk_app.region,
                "owner_username": "user1",
                "app_code": bk_app.code,
                "app_secret": "nosec",
                "app_name": bk_app.name,
            },
        )

        # 验证 Git 操作被调用
        mock_fix_config.assert_called_once()
        mocked_client.clone.assert_called_once()
        mocked_client.add.assert_called_once()
        mocked_client.commit.assert_called_once()
        mocked_client.push.assert_called_once()
