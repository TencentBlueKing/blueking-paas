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

import uuid

import pytest
from django_dynamic_fixture import G

from paasng.platform.engine.models import Deployment
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.models import VersionInfo

pytestmark = pytest.mark.django_db


class TestDeploymentVersion:
    """测试获取 Deployment 关联的源代码版本信息"""

    def test_source_code(self, bk_module, bk_stag_env):
        """测试从源码构建时的版本信息"""
        deployment = G(
            Deployment,
            app_environment=bk_stag_env,
            source_version_type="tag",
            source_version_name="v1.2.3",
            source_revision="hash",
        )
        assert deployment.get_version_info() == VersionInfo(revision="hash", version_name="v1.2.3", version_type="tag")

    def test_s_mart(self, bk_module, bk_stag_env):
        """测试 S-Mart 镜像应用查询源码包版本信息"""

        bk_module.source_origin = SourceOrigin.S_MART
        bk_module.save()
        deployment = G(
            Deployment,
            app_environment=bk_stag_env,
            source_version_type="tag",
            source_version_name="v1.2.3",
            source_revision="hash",
        )
        assert deployment.get_version_info() == VersionInfo(revision="hash", version_name="v1.2.3", version_type="tag")

    def test_image(self, bk_module, bk_stag_env, bk_prod_env):
        """测试发布历史镜像时, 查询镜像对应的源码版本信息"""

        build_id = uuid.uuid4()
        bk_module.save()
        G(
            Deployment,
            build_id=build_id,
            app_environment=bk_stag_env,
            source_version_type="tag",
            source_version_name="v1.2.3",
            source_revision="hash",
        )

        deployment = G(
            Deployment,
            app_environment=bk_prod_env,
            source_version_type="image",
            source_version_name="v1.2.3",
            source_revision="hash",
            build_id=build_id,
        )
        assert deployment.get_version_info() == VersionInfo(revision="hash", version_name="v1.2.3", version_type="tag")
