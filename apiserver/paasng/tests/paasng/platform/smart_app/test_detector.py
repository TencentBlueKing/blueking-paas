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
import pytest
import yaml
from rest_framework.exceptions import ValidationError

from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.smart_app.utils.app_desc import get_app_description
from paasng.platform.smart_app.utils.detector import (
    AppYamlDetector,
    DetectResult,
    ManifestDetector,
    SourcePackageStatReader,
)
from tests.paasng.platform.sourcectl.packages.utils import EXAMPLE_APP_YAML

pytestmark = pytest.mark.django_db


class TestAppYamlDetector:
    @pytest.mark.parametrize(
        ("spec_version", "filepath", "expected"),
        [
            (AppSpecVersion.VER_1, "app.yaml", DetectResult("", AppSpecVersion.VER_1)),
            (AppSpecVersion.VER_1, "app.yml", DetectResult("", AppSpecVersion.VER_1)),
            (AppSpecVersion.VER_1, "./app.yaml", DetectResult("./", AppSpecVersion.VER_1)),
            (AppSpecVersion.VER_1, "path/to/app.yaml", DetectResult("path/to/", AppSpecVersion.VER_1)),
            (AppSpecVersion.VER_1, "E:\\app.yaml", DetectResult("E:\\", AppSpecVersion.VER_1)),
            (AppSpecVersion.VER_1, "app_desc.yaml", None),
            (AppSpecVersion.VER_1, "app_desc.yml", None),
            (AppSpecVersion.VER_1, "./app_desc.yaml", None),
            (AppSpecVersion.VER_1, "path/to/app_desc.yaml", None),
            (AppSpecVersion.VER_1, "E:\\app_desc.yaml", None),
            (AppSpecVersion.VER_2, "app.yaml", None),
            (AppSpecVersion.VER_2, "app.yml", None),
            (AppSpecVersion.VER_2, "./app.yaml", None),
            (AppSpecVersion.VER_2, "path/to/app.yaml", None),
            (AppSpecVersion.VER_2, "E:\\app.yaml", None),
            (AppSpecVersion.VER_2, "app_desc.yaml", DetectResult("", AppSpecVersion.VER_2)),
            (AppSpecVersion.VER_2, "app_desc.yml", DetectResult("", AppSpecVersion.VER_2)),
            (AppSpecVersion.VER_2, "./app_desc.yaml", DetectResult("./", AppSpecVersion.VER_2)),
            (AppSpecVersion.VER_2, "path/to/app_desc.yaml", DetectResult("path/to/", AppSpecVersion.VER_2)),
            (AppSpecVersion.VER_2, "E:\\app_desc.yaml", DetectResult("E:\\", AppSpecVersion.VER_2)),
            (AppSpecVersion.VER_1, "._app.yaml", None),
            (AppSpecVersion.VER_1, "./._app.yaml", None),
            (AppSpecVersion.VER_1, "xxxapp.yaml", None),
            (AppSpecVersion.VER_1, "./xxxapp.yaml", None),
            (AppSpecVersion.VER_2, "._app_desc.yaml", None),
            (AppSpecVersion.VER_2, "./._app_desc.yaml", None),
            (AppSpecVersion.VER_2, "xxxapp_desc.yaml", None),
            (AppSpecVersion.VER_2, "./xxxapp_desc.yaml", None),
        ],
    )
    def test_detect(self, spec_version, filepath, expected):
        assert AppYamlDetector.detect(filepath, spec_version) == expected


@pytest.mark.parametrize("package_root", ["untar_path", "zip_path"], indirect=["package_root"])
class TestManifestDetector:
    @pytest.mark.parametrize(
        ("contents", "error"),
        [
            ({"app.yaml": yaml.dump(EXAMPLE_APP_YAML)}, KeyError("Procfile not found.")),
            ({"foo/app.yaml": yaml.dump(EXAMPLE_APP_YAML)}, KeyError("Procfile not found.")),
        ],
    )
    def test_error(self, package_root, package_stat, contents, error):
        with pytest.raises(KeyError) as e:
            ManifestDetector(
                package_root=package_root,
                app_description=get_app_description(package_stat),
                relative_path=package_stat.relative_path,
            ).detect()
        assert str(e.value) == str(error)

    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ({"app.yaml": yaml.dump(EXAMPLE_APP_YAML)}, "./app.yaml"),
            ({"foo/app.yaml": yaml.dump(EXAMPLE_APP_YAML)}, "./app.yaml"),
        ],
    )
    def test_detect_app_desc(self, package_root, package_stat, contents, expected):
        assert (
            ManifestDetector(
                package_root=package_root,
                app_description=get_app_description(package_stat),
                relative_path=package_stat.relative_path,
            ).detect_app_desc()
            == expected
        )

    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ({"app.yaml": yaml.dump(EXAMPLE_APP_YAML)}, None),
            (
                {"foo/app.yaml": yaml.dump(EXAMPLE_APP_YAML), "foo/src/requirements.txt": ""},
                "./src/requirements.txt",
            ),
            ({"foo/app.yaml": yaml.dump(EXAMPLE_APP_YAML), "src/requirements.txt": ""}, None),
        ],
    )
    def test_detect_dependency(self, package_root, package_stat, contents, expected):
        assert (
            ManifestDetector(
                package_root=package_root,
                app_description=get_app_description(package_stat),
                relative_path=package_stat.relative_path,
            ).detect_dependency()
            == expected
        )

    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ({"app.yaml": yaml.dump(EXAMPLE_APP_YAML)}, {}),
            (
                {"foo/app.yaml": yaml.dump(EXAMPLE_APP_YAML), "foo/cert/bk_root_ca.cert": ""},
                {"root": "./cert/bk_root_ca.cert"},
            ),
            (
                {
                    "foo/app.yaml": yaml.dump(EXAMPLE_APP_YAML),
                    "foo/cert/bk_root_ca.cert": "",
                    "foo/cert/bk_saas_sign.cert": "",
                },
                {"root": "./cert/bk_root_ca.cert", "intermediate": "./cert/bk_saas_sign.cert"},
            ),
        ],
    )
    def test_detect_certs(self, package_root, package_stat, contents, expected):
        assert (
            ManifestDetector(
                package_root=package_root,
                app_description=get_app_description(package_stat),
                relative_path=package_stat.relative_path,
            ).detect_certs()
            == expected
        )

    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ({"app.yaml": yaml.dump(EXAMPLE_APP_YAML)}, {}),
            (
                {"bar/app.yaml": yaml.dump(EXAMPLE_APP_YAML), "bar/conf/SHA256": ""},
                {"sha256": "./conf/SHA256"},
            ),
            (
                {"bar/app.yaml": yaml.dump(EXAMPLE_APP_YAML), "bar/conf/SHA256": "", "./bar/conf/package.conf": ""},
                {"sha256": "./conf/SHA256", "package": "./conf/package.conf"},
            ),
        ],
    )
    def test_detect_encryption(self, package_root, package_stat, contents, expected):
        assert (
            ManifestDetector(
                package_root=package_root,
                app_description=get_app_description(package_stat),
                relative_path=package_stat.relative_path,
            ).detect_encryption()
            == expected
        )


class TestSourcePackageStatReader:
    @pytest.mark.parametrize(
        ("contents", "expected_meta_info", "expected_relative_path"),
        [
            # 我们的打包脚本会默认打成相对路径形式
            ({"app.yaml": yaml.dump({"version": "v1"})}, {"version": "v1"}, "./"),
            ({"./app.yaml": yaml.dump({"version": "v1"})}, {"version": "v1"}, "./"),
            ({"app_code/app.yaml": yaml.dump({"version": "v1"})}, {"version": "v1"}, "./app_code/"),
            ({"app.yml": yaml.dump({"name": "v1"})}, {"name": "v1"}, "./"),
            ({"./app.yml": yaml.dump({"name": "v1"})}, {"name": "v1"}, "./"),
            ({"app_code/app.yml": yaml.dump({"name": "v1"})}, {"name": "v1"}, "./app_code/"),
            ({"Procfile": ""}, {}, "./"),
            ({"foo": yaml.dump({"version": "v1"})}, {}, "./"),
        ],
    )
    def test_get_meta_info(self, tar_path, expected_meta_info, expected_relative_path):
        relative_path, meta_info = SourcePackageStatReader(tar_path).get_meta_info()
        assert meta_info == expected_meta_info
        assert relative_path == expected_relative_path

    @pytest.mark.parametrize("contents", [{"app.yaml": "invalid-: yaml: content"}])
    def test_invalid_file_format(self, tar_path):
        with pytest.raises(ValidationError):
            SourcePackageStatReader(tar_path).get_meta_info()

    @pytest.mark.parametrize(
        ("contents", "meta_info", "version"),
        [
            ({"app.yaml": yaml.dump(EXAMPLE_APP_YAML)}, EXAMPLE_APP_YAML, EXAMPLE_APP_YAML["version"]),
            (
                {"app.yaml": yaml.dump(EXAMPLE_APP_YAML), "logo.png": "dummy"},
                {"logo_b64data": "base64,ZHVtbXk=", "logoB64data": "base64,ZHVtbXk=", **EXAMPLE_APP_YAML},
                EXAMPLE_APP_YAML["version"],
            ),
        ],
    )
    def test_read(self, tar_path, meta_info, version):
        stat = SourcePackageStatReader(tar_path).read()
        assert stat.meta_info == meta_info
        assert stat.version == version
