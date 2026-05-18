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
from django_dynamic_fixture import G

from paas_wl.bk_app.applications.models import Build
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.views.deploy import DeploymentViewSet
from paasng.platform.sourcectl.constants import VersionType
from paasng.platform.sourcectl.models import VersionInfo

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestDeploymentViewSetGetVersionInfo:
    """测试部署入口构造版本信息"""

    def test_custom_image_uses_tag_as_revision(self, bk_user, bk_module):
        """仅镜像应用使用镜像 tag 作为 revision"""
        bk_module.build_config.build_method = RuntimeType.CUSTOM_IMAGE
        bk_module.build_config.save()

        version_info = DeploymentViewSet._get_version_info(
            user=bk_user,
            module=bk_module,
            params={"version_name": "v1.2.3"},
        )

        assert version_info == VersionInfo(
            revision="v1.2.3",
            version_name="v1.2.3",
            version_type=VersionType.TAG.value,
        )

    def test_built_image_uses_build_image_tag_as_revision(self, bk_user, bk_module):
        """历史构建镜像部署使用构建镜像 tag 作为 revision"""
        build = G(Build, image="bkapp:build-v1.2.3")

        version_info = DeploymentViewSet._get_version_info(
            user=bk_user,
            module=bk_module,
            params={"version_name": "v1.2.3"},
            build=build,
        )

        assert version_info == VersionInfo(
            revision="build-v1.2.3",
            version_name="build-v1.2.3",
            version_type=VersionType.IMAGE.value,
        )

    def test_source_code_uses_extracted_revision(self, bk_user, bk_module):
        """源码部署优先使用版本服务解析出的 revision"""
        service = mock.MagicMock()
        service.extract_smart_revision.return_value = "commit-sha"

        with mock.patch("paasng.platform.engine.views.deploy.get_version_service", return_value=service):
            version_info = DeploymentViewSet._get_version_info(
                user=bk_user,
                module=bk_module,
                params={"version_name": "v1.2.3", "version_type": VersionType.TAG.value, "revision": "input-sha"},
            )

        service.extract_smart_revision.assert_called_once_with("tag:v1.2.3")
        assert version_info == VersionInfo(
            revision="commit-sha",
            version_name="v1.2.3",
            version_type=VersionType.TAG.value,
        )
