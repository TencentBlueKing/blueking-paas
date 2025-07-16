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

import tarfile

import pytest
import yaml

from paasng.platform.declarative import constants
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.patcher import patch_smart_tarball
from paasng.platform.sourcectl.utils import generate_temp_dir
from tests.paasng.platform.sourcectl.packages.utils import V1_APP_DESC_EXAMPLE

pytestmark = pytest.mark.django_db
EXPECTED_WEB_PROCESS = constants.WEB_PROCESS


class Test__patch_smart_tarball:
    @pytest.fixture()
    def patched_tar(self, tar_path, bk_module_full):
        bk_module_full.name = "bar"
        bk_module_full.source_origin = SourceOrigin.BK_LESS_CODE.value
        stat = SourcePackageStatReader(tar_path).read()
        with generate_temp_dir() as dest_dir:
            dest = patch_smart_tarball(tarball_path=tar_path, dest_dir=dest_dir, module=bk_module_full, stat=stat)
            yield dest

    @pytest.mark.parametrize(
        "contents",
        [
            {"app.yaml": yaml.safe_dump(V1_APP_DESC_EXAMPLE)},
        ],
    )
    def test_error_if_patch_unsupported_ver(self, bk_module_full, tar_path, tmp_path):
        """Test if the patcher raises an error when the app description file is v1."""
        bk_module_full.name = "bar"
        bk_module_full.source_origin = SourceOrigin.BK_LESS_CODE.value
        stat = SourcePackageStatReader(tar_path).read()

        with pytest.raises(DescriptionValidationError):
            patch_smart_tarball(tarball_path=tar_path, dest_dir=tmp_path, module=bk_module_full, stat=stat)

    @pytest.mark.parametrize(
        ("contents", "target", "expected"),
        [
            (
                {
                    "foo/app_desc.yaml": yaml.dump(
                        {
                            "spec_version": 2,
                            "app": {"bk_app_code": "foo", "bk_app_name": "foo"},
                            "modules": {
                                "bar": {
                                    "language": "python",
                                    "is_default": True,
                                    "processes": {"hello": {"command": "echo 'hello world!';"}},
                                }
                            },
                        }
                    )
                },
                "./foo/Procfile",
                # shlex 在某些情况会出现稍微偏差(这里的 ; 号位置变了)
                {"hello": "echo 'hello world!';"},
            ),
            # 测试 Procfile 不会被覆盖
            (
                {
                    "foo/app_desc.yaml": yaml.dump(
                        {
                            "spec_version": 2,
                            "app": {"bk_app_code": "foo", "bk_app_name": "foo"},
                            "modules": {
                                "bar": {
                                    "language": "python",
                                    "is_default": True,
                                    "processes": {"hello": {"command": "echo 'good afternoon!';"}},
                                }
                            },
                        }
                    ),
                    "foo/Procfile": yaml.dump({"hello": "echo 'good morning!';"}),
                },
                "./foo/Procfile",
                {"hello": "echo 'good morning!';"},
            ),
            # 测试多模块.
            (
                {
                    "foo/app_desc.yaml": yaml.dump(
                        {
                            "spec_version": 2,
                            "app": {"bk_app_code": "foo", "bk_app_name": "foo"},
                            "modules": {
                                "bar": {
                                    "is_default": True,
                                    "processes": {"hello": {"command": "echo 'Hello Foo, i am Bar!'"}},
                                    "source_dir": "./src/bar",
                                    "language": "python",
                                },
                                "foo": {
                                    "processes": {"hello": {"command": "echo 'Hello Bar, i am Foo!'"}},
                                    "source_dir": "./src/foo",
                                    "language": "python",
                                },
                            },
                        }
                    ),
                    "foo/src/bar": [],
                    "foo/src/foo": [],
                },
                "./foo/src/bar/Procfile",
                {"hello": "echo 'Hello Foo, i am Bar!'"},
            ),
        ],
    )
    def test_add_procfile(self, tar_path, patched_tar, target, expected):
        assert tar_path.name == patched_tar.name
        with tarfile.open(patched_tar) as tar:
            fp = tar.extractfile(target)
            assert fp
            data = yaml.safe_load(fp.read())
            assert data == expected
