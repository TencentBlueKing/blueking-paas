# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from unittest import mock

import pytest

from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.engine.helpers import RuntimeInfo
from paasng.platform.modules.constants import SourceOrigin

pytestmark = pytest.mark.django_db


@pytest.fixture
def version():
    return VersionInfo(revision='foo', version_type='tag', version_name='foo')


class TestRuntimeInfo:
    @pytest.mark.parametrize(
        "source_origin, expected",
        [(SourceOrigin.IMAGE_REGISTRY, "docker.io/library/python:foo"), (SourceOrigin.AUTHORIZED_VCS, "")],
    )
    def test_image(self, bk_module_full, version, source_origin, expected):
        bk_module_full.source_origin = source_origin.value
        bk_module_full.save()
        runtime_info = RuntimeInfo(bk_module_full.get_envs("prod").get_engine_app(), version)
        with mock.patch.object(runtime_info.module, "get_source_obj") as m:
            m().get_repo_url.return_value = "docker.io/library/python"

            assert runtime_info.image == expected

    @pytest.mark.parametrize(
        "source_origin, expected",
        [(SourceOrigin.IMAGE_REGISTRY, "custom_image"), (SourceOrigin.AUTHORIZED_VCS, "buildpack")],
    )
    def test_type(self, bk_module_full, version, source_origin, expected):
        bk_module_full.source_origin = source_origin.value
        bk_module_full.save()
        runtime_info = RuntimeInfo(bk_module_full.get_envs("prod").get_engine_app(), version)

        assert runtime_info.type == expected
