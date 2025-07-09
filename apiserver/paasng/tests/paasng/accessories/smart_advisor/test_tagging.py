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
import tempfile
from pathlib import Path
from textwrap import dedent
from unittest import mock

import pytest
from django_dynamic_fixture import G

from paasng.accessories.smart_advisor.constants import DeployFailurePatternType
from paasng.accessories.smart_advisor.models import DeployFailurePattern
from paasng.accessories.smart_advisor.tagging import dig_tags_local_repo, get_deployment_tags
from paasng.accessories.smart_advisor.tags import DeploymentFailureTag, force_tag
from tests.paasng.platform.engine.setup_utils import create_fake_deployment

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


class TestTaggingLocalPath:
    @pytest.mark.parametrize("encoding", ["utf-8", "gbk"])
    def test_tagging_python_using_different_encodings(self, encoding):
        repo_path = Path(tempfile.mkdtemp())
        with open(repo_path / "requirements.txt", "w", encoding=encoding) as fp:
            fp.write(
                dedent(
                    """\
            # 中文非 ascii 字符
            Django==1.11.2
            blueapps==1.0.15
            gunicorn==19.6.0
            blueking.component.ieod>=0.0.39
            raven==6.1.0"""
                )
            )

        assert set(dig_tags_local_repo(repo_path)) == {
            force_tag("app-pl:python"),
            force_tag("app-sdk:django"),
            force_tag("app-sdk:gunicorn"),
            force_tag("app-sdk:blueapps"),
        }

    def test_tagging_php(self):
        repo_path = Path(tempfile.mkdtemp())
        with open(repo_path / "server.php", "w") as fp:
            fp.write("")

        assert set(dig_tags_local_repo(repo_path)) == {
            force_tag("app-pl:php"),
        }

    def test_tagging_go(self):
        repo_path = Path(tempfile.mkdtemp())
        with open(repo_path / "main.go", "w") as fp:
            fp.write("")

        assert set(dig_tags_local_repo(repo_path)) == {
            force_tag("app-pl:go"),
        }

    def test_tagging_nodejs(self):
        repo_path = Path(tempfile.mkdtemp())
        with open(repo_path / "package.json", "w") as fp:
            fp.write("")
        with open(repo_path / "index.js", "w") as fp:
            fp.write("")

        assert set(dig_tags_local_repo(repo_path)) == {
            force_tag("app-pl:nodejs"),
        }


class TestGetDeploymentTags:
    def setup_data(self):
        pattern_data = [
            ("Procfile error:", "deploy-failure:fix_procfile"),
            ("Unable to install mysql-client", "deploy-failure:fix_mysql_installation"),
            ("中文错误", "deploy-failure:ch-err"),
        ]
        for value, tag_str in pattern_data:
            G(DeployFailurePattern, type=DeployFailurePatternType.REGULAR_EXPRESSION, value=value, tag_str=tag_str)

    @pytest.mark.parametrize(
        ("logs", "tags"),
        [
            ("Procfile error: blabla", [DeploymentFailureTag("fix_procfile")]),
            ("ops, unable to install mysql-client, reason: unknown", [DeploymentFailureTag("fix_mysql_installation")]),
            ("foo 中文错误 bar", [DeploymentFailureTag("ch-err")]),
            ("no errors", []),
        ],
    )
    def test_normal(self, bk_module, logs, tags):
        self.setup_data()

        deployment = create_fake_deployment(bk_module)
        with mock.patch("paasng.accessories.smart_advisor.tagging.get_all_logs", return_value=logs):
            results = get_deployment_tags(deployment)
            assert results == tags
