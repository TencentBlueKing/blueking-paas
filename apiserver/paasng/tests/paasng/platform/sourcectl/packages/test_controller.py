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
from unittest import mock

import pytest
import yaml
from blue_krill.contextlib import nullcontext as does_not_raise

from paasng.platform.engine.configurations.source_file import get_metadata_reader
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.sourcectl.controllers.package import PackageController
from paasng.platform.sourcectl.exceptions import GetProcfileError
from paasng.platform.sourcectl.models import AlternativeVersion, SourcePackage, SPStoragePolicy, VersionInfo
from paasng.platform.sourcectl.package.client import TarClient, ZipClient
from paasng.platform.sourcectl.utils import generate_temp_dir, generate_temp_file
from tests.paasng.platform.sourcectl.packages.utils import gen_tar, gen_zip

pytestmark = pytest.mark.django_db


@pytest.fixture()
def package_module(bk_module):
    bk_module.name = "default"
    bk_module.source_origin = 2
    bk_module.save()
    return bk_module


class TestPackageRepoController:
    @pytest.mark.parametrize(
        ("archive_maker", "archive_client_cls"),
        [(gen_tar, TarClient), (gen_zip, ZipClient)],
    )
    @pytest.mark.parametrize(
        ("contents", "expected_ctx"),
        [
            (
                {
                    "app_desc.yaml": yaml.dump(
                        {
                            "spec_version": 2,
                            "app": {"region": "default", "bk_app_code": "foo", "bk_app_name": "foo"},
                            "modules": {
                                "default": {
                                    "language": "python",
                                    "is_default": True,
                                    "processes": {"web": {"command": "npm run dev\n"}},
                                }
                            },
                        }
                    )
                },
                does_not_raise({"web": "npm run dev"}),
            ),
            # 从应用文件读取进程信息会校验大小写(因为 validations 规则中已经检查过大小写)
            # p.s. 一般情况不会触发该异常(因为源码包在保存时已经校验过一次应用描述文件)
            (
                {
                    "app_desc.yaml": yaml.dump(
                        {
                            "spec_version": 2,
                            "app": {"region": "default", "bk_app_code": "foo", "bk_app_name": "foo"},
                            "modules": {
                                "default": {
                                    "language": "python",
                                    "is_default": True,
                                    "processes": {"Web": {"command": "npm run dev\n"}},
                                }
                            },
                        }
                    )
                },
                pytest.raises(GetProcfileError),
            ),
            # 测试 SourcePackage 没有记录 metadata 的情况
            ({"Procfile": "web: npm run dev\n"}, does_not_raise({"web": "npm run dev"})),
            ({"Procfile": "Web: npm run dev\n"}, does_not_raise({"Web": "npm run dev"})),
        ],
    )
    def test_read_file(self, bk_user, package_module, archive_maker, archive_client_cls, contents, expected_ctx):
        version_info = VersionInfo(revision="v1", version_type="package", version_name="")
        with generate_temp_file() as file_path:
            archive_maker(file_path, contents)
            stat = SourcePackageStatReader(file_path).read()
            stat.version = version_info.revision
            package = SourcePackage.objects.store(
                package_module,
                SPStoragePolicy(path=str(file_path), url="don't care", stat=stat),
                operator=bk_user,
            )

            with mock.patch(
                "paasng.platform.engine.configurations.source_file.PackageMetaDataReader.get_client",
                return_value=archive_client_cls(package.storage_path, relative_path=package.relative_path),
            ):
                controller = get_metadata_reader(package_module)
                with expected_ctx as expected:
                    assert controller.get_procfile(version_info) == expected

    @pytest.mark.parametrize(
        ("archive_maker", "archive_client_cls"),
        [(gen_tar, TarClient), (gen_zip, ZipClient)],
    )
    @pytest.mark.parametrize(
        "contents",
        [
            ({"Procfile": "web: npm run dev\n"}),
        ],
    )
    def test_export(self, bk_user, package_module, archive_maker, archive_client_cls, contents):
        version_info = VersionInfo(revision="v1", version_type="package", version_name="")
        with generate_temp_file() as file_path, generate_temp_dir() as working_dir:
            archive_maker(file_path, contents)
            controller = PackageController.init_by_module(package_module)
            stat = SourcePackageStatReader(file_path).read()
            stat.version = version_info.revision
            package = SourcePackage.objects.store(
                package_module,
                SPStoragePolicy(path=str(file_path), url="don't care", stat=stat),
                operator=bk_user,
            )

            with mock.patch(
                "paasng.platform.sourcectl.controllers.package.PackageController.get_client",
                return_value=archive_client_cls(package.storage_path, relative_path=package.relative_path),
            ):
                controller.export(working_dir, version_info=version_info)
                assert {str(child.relative_to(working_dir)) for child in working_dir.iterdir()} == set(contents.keys())

    @pytest.mark.parametrize(
        ("versions", "expected"),
        [
            ([], []),
            (
                [
                    VersionInfo(revision="v1", version_type="package", version_name=""),
                ],
                [dict(name="v1", revision="v1", type="package", url="", last_update=..., extra=dict())],
            ),
            (
                [
                    VersionInfo(revision="v1", version_type="package", version_name=""),
                    VersionInfo(revision="v2", version_type="package", version_name=""),
                ],
                [
                    dict(name="v1", revision="v1", type="package", url="", last_update=..., extra=dict()),
                    dict(name="v2", revision="v2", type="package", url="", last_update=..., extra=dict()),
                ],
            ),
        ],
    )
    def test_list_alternative_versions(self, package_module, versions, expected, tmp_path):
        # Write an empty tarfile to avoid file format exception when the reader is trying to
        # parse the file.
        file_path = tmp_path / "foo.tgz"
        with tarfile.open(file_path, "w:gz"):
            pass

        for idx, version_info in enumerate(versions):
            stat = SourcePackageStatReader(file_path).read()
            stat.version = version_info.revision
            package = SourcePackage.objects.store(
                package_module,
                SPStoragePolicy(
                    engine="TarClient",
                    path=str(file_path),
                    url=f"scheme://bucket/{file_path}",
                    stat=stat,
                ),
            )
            package.refresh_from_db()
            expected[idx]["url"] = package.storage_url
            expected[idx]["last_update"] = package.updated
            expected[idx]["extra"]["package_size"] = package.package_size
            expected[idx]["extra"]["is_deleted"] = package.is_deleted

        controller = PackageController.init_by_module(package_module)
        assert controller.list_alternative_versions() == [AlternativeVersion(**item) for item in expected]
