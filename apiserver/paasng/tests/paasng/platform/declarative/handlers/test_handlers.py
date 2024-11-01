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

from textwrap import dedent

import pytest
import yaml

from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_deploy_desc_handler, get_desc_handler

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGetAppDescHandlerIncorrectVersions:
    def test_ver_1(self, bk_user):
        yaml_content = dedent(
            """
        app_code: foo
        app_name: foo
        """
        )

        with pytest.raises(DescriptionValidationError, match='version "1" is not supported'):
            get_desc_handler(yaml.safe_load(yaml_content)).handle_app(bk_user)

    def test_ver_unspecified(self, bk_user):
        yaml_content = dedent(
            """
        bk_app_code: foo
        bk_app_name: foo
        """
        )

        with pytest.raises(DescriptionValidationError, match="No spec version is specified"):
            get_desc_handler(yaml.safe_load(yaml_content)).handle_app(bk_user)

    def test_ver_unknown_number(self, bk_user):
        yaml_content = "spec_version: 999"

        with pytest.raises(DescriptionValidationError, match='version "999" is not supported'):
            get_desc_handler(yaml.safe_load(yaml_content)).handle_app(bk_user)

    def test_ver_unknown_string(self, bk_user):
        yaml_content = "spec_version: foobar"

        with pytest.raises(DescriptionValidationError, match='version "foobar" is not supported'):
            get_desc_handler(yaml.safe_load(yaml_content)).handle_app(bk_user)


class TestGetDeployDescHandlerIncorrectVersions:
    def test_ver_1(self, bk_user):
        yaml_content = dedent(
            """
        app_code: foo
        app_name: foo
        """
        )

        with pytest.raises(ValueError, match='version "1" is not supported'):
            get_deploy_desc_handler(yaml.safe_load(yaml_content))

    def test_ver_unspecified(self, bk_user):
        yaml_content = dedent(
            """
        bk_app_code: foo
        bk_app_name: foo
        """
        )

        with pytest.raises(ValueError, match="no spec version is specified"):
            get_deploy_desc_handler(yaml.safe_load(yaml_content))

    def test_ver_unknown_number(self, bk_user):
        yaml_content = "spec_version: 999"

        with pytest.raises(ValueError, match='version "999" is not supported'):
            get_deploy_desc_handler(yaml.safe_load(yaml_content))

    def test_ver_unknown_string(self, bk_user):
        yaml_content = "spec_version: foobar"

        with pytest.raises(ValueError, match='version "foobar" is not supported'):
            get_deploy_desc_handler(yaml.safe_load(yaml_content))
