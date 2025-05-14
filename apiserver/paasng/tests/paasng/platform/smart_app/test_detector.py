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
import yaml
from rest_framework.exceptions import ValidationError

from paasng.platform.smart_app.services.app_desc import get_app_description
from paasng.platform.smart_app.services.detector import (
    ManifestDetector,
    SourcePackageStatReader,
    relative_path_of_app_desc,
)
from tests.paasng.platform.sourcectl.packages.utils import V2_APP_DESC_EXAMPLE

pytestmark = pytest.mark.django_db


class Test__relative_path_of_app_desc:
    @pytest.mark.parametrize(
        ("filepath", "expected"),
        [
            ("app_desc.yaml", ""),
            ("app_desc.yml", ""),
            ("./app_desc.yaml", "./"),
            ("path/to/app_desc.yaml", "path/to/"),
            ("E:\\app_desc.yaml", "E:\\"),
            # Not a app desc file
            ("foo/bar.txt", None),
            ("._app_desc.yaml", None),
            ("./._app_desc.yaml", None),
            ("xxxapp_desc.yaml", None),
            ("./xxxapp_desc.yaml", None),
            # Legacy app_desc file names are not supported
            ("app.yaml", None),
            ("app.yml", None),
        ],
    )
    def test_detect(self, filepath, expected):
        assert relative_path_of_app_desc(filepath) == expected


@pytest.mark.parametrize("package_root", ["untar_path", "zip_path"], indirect=["package_root"])
class TestManifestDetector:
    @pytest.fixture
    def detector(self, package_root, package_stat) -> ManifestDetector:
        """The detector instance for testing."""
        return ManifestDetector(
            package_root=package_root,
            app_description=get_app_description(package_stat),
            relative_path=package_stat.relative_path,
        )

    @pytest.mark.parametrize(
        ("contents", "error"),
        [
            ({"app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE)}, "Procfile not found."),
            ({"foo/app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE)}, "Procfile not found."),
        ],
    )
    def test_only_app_desc_file(self, detector, contents, error):
        with pytest.raises(KeyError, match=error):
            detector.detect()

    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ({"app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE)}, "./app_desc.yaml"),
            ({"foo/app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE)}, "./app_desc.yaml"),
        ],
    )
    def test_detect_app_desc(self, detector, contents, expected):
        assert detector.detect_app_desc() == expected

    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ({"app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE)}, None),
            (
                {"foo/app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE), "foo/src/requirements.txt": ""},
                "./src/requirements.txt",
            ),
            # Not in the same directories
            ({"foo/app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE), "src/requirements.txt": ""}, None),
        ],
    )
    def test_detect_dependency(self, detector, contents, expected):
        assert detector.detect_dependency() == expected

    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ({"app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE)}, {}),
            (
                {"foo/app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE), "foo/cert/bk_root_ca.cert": ""},
                {"root": "./cert/bk_root_ca.cert"},
            ),
            (
                {
                    "foo/app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE),
                    "foo/cert/bk_root_ca.cert": "",
                    "foo/cert/bk_saas_sign.cert": "",
                },
                {"root": "./cert/bk_root_ca.cert", "intermediate": "./cert/bk_saas_sign.cert"},
            ),
        ],
    )
    def test_detect_certs(self, detector, contents, expected):
        assert detector.detect_certs() == expected

    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ({"app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE)}, {}),
            (
                {"bar/app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE), "bar/conf/SHA256": ""},
                {"sha256": "./conf/SHA256"},
            ),
            (
                {
                    "bar/app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE),
                    "bar/conf/SHA256": "",
                    "./bar/conf/package.conf": "",
                },
                {"sha256": "./conf/SHA256", "package": "./conf/package.conf"},
            ),
        ],
    )
    def test_detect_encryption(self, detector, contents, expected):
        assert detector.detect_encryption() == expected


class TestSourcePackageStatReader:
    # The simple description data for validations
    desc_data = {"foo": "bar"}
    desc_data_str = yaml.safe_dump(desc_data)

    @pytest.mark.parametrize(
        ("contents", "expected_relative_path"),
        [
            # 打包脚本默认使用相对路径形式
            ({"app_desc.yaml": desc_data_str}, "./"),
            ({"./app_desc.yaml": desc_data_str}, "./"),
            ({"app_code/app_desc.yaml": desc_data_str}, "./app_code/"),
            ({"app_desc.yml": desc_data_str}, "./"),
        ],
    )
    def test_get_meta_info_found_desc_file(self, contents, tar_path, expected_relative_path):
        relative_path, meta_info = SourcePackageStatReader(tar_path).get_meta_info()
        assert meta_info == self.desc_data
        assert relative_path == expected_relative_path

    @pytest.mark.parametrize(
        "contents",
        [
            {"Procfile": ""},
            {"foo": desc_data_str},
        ],
    )
    def test_get_meta_info_no_desc_file(self, tar_path):
        relative_path, meta_info = SourcePackageStatReader(tar_path).get_meta_info()
        assert meta_info == {}
        assert relative_path == "./"

    @pytest.mark.parametrize("contents", [{"app_desc.yaml": "invalid-: yaml: content"}])
    def test_invalid_file_format(self, tar_path):
        with pytest.raises(ValidationError):
            SourcePackageStatReader(tar_path).get_meta_info()

    @pytest.mark.parametrize(
        ("contents", "meta_info", "version"),
        [
            (
                {"app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE)},
                V2_APP_DESC_EXAMPLE,
                V2_APP_DESC_EXAMPLE["app_version"],
            ),
            (
                {"app_desc.yaml": yaml.dump(V2_APP_DESC_EXAMPLE), "logo.png": "dummy"},
                {"logo_b64data": "base64,ZHVtbXk=", "logoB64data": "base64,ZHVtbXk="} | V2_APP_DESC_EXAMPLE,
                V2_APP_DESC_EXAMPLE["app_version"],
            ),
        ],
    )
    def test_read(self, tar_path, meta_info, version):
        stat = SourcePackageStatReader(tar_path).read()
        assert stat.meta_info == meta_info
        assert stat.version == version
