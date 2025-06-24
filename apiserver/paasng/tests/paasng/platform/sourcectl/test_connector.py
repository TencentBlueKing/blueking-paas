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

import pytest
from django.conf import settings

from paasng.platform.sourcectl.connector import ExternalGitAppRepoConnector, IntegratedSvnAppRepoConnector
from paasng.platform.sourcectl.source_types import get_sourcectl_types

pytestmark = pytest.mark.django_db


class TestIntegratedSvnAppRepoConnector:
    @pytest.mark.usefixtures("_init_tmpls")
    def test_normal(self, bk_module):
        bk_module.source_init_template = settings.DUMMY_TEMPLATE_NAME

        connector = IntegratedSvnAppRepoConnector(bk_module, get_sourcectl_types().names.bk_svn)
        repo_url = "svn://svn.example.com/app/a/"
        connector.bind(repo_url)


class TestExternalGitAppRepoConnector:
    @pytest.mark.usefixtures("_init_tmpls")
    def test_normal(self, bk_app, bk_module):
        bk_module.source_init_template = settings.DUMMY_TEMPLATE_NAME

        connector = ExternalGitAppRepoConnector(bk_module, "--placeholder--")
        connector.bind("git://git.example.com/some-proj.git")
