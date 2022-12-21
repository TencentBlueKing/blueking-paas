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

from paasng.dev_resources.sourcectl.controllers.package import PackageController
from paasng.dev_resources.sourcectl.models import AlternativeVersion, SourcePackage, SPStoragePolicy, VersionInfo
from paasng.dev_resources.sourcectl.utils import generate_temp_dir, generate_temp_file
from paasng.engine.deploy.metadata import get_metadata_reader
from paasng.extensions.smart_app.detector import SourcePackageStatReader
from tests.sourcectl.packages.utils import gen_tar, gen_zip

pytestmark = pytest.mark.django_db


@pytest.fixture
def package_module(bk_module):
    bk_module.name = "default"
    bk_module.source_origin = 2
    bk_module.save()
    yield bk_module


class TestPackageRepoController:
    @pytest.mark.parametrize("engine, archive_maker", [("TarClient", gen_tar), ("ZipClient", gen_zip)])
    @pytest.mark.parametrize(
        "contents, expected",
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
                {"web": "npm run dev"},
            ),
            # get_procfile 不会进行格式化.
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
                {"Web": "npm run dev"},
            ),
            # 测试 SourcePackage 没有记录 metadata 的情况
            ({"Procfile": "web: npm run dev\n"}, {"web": "npm run dev"}),
            ({"Procfile": "Web: npm run dev\n"}, {"Web": "npm run dev"}),
        ],
    )
    def test_read_file(self, bk_user, package_module, engine, archive_maker, contents, expected):
        version_info = VersionInfo(revision="v1", version_type="package", version_name="")
        with generate_temp_file() as file_path:
            archive_maker(file_path, contents)
            stat = SourcePackageStatReader(file_path).read()
            stat.version = version_info.revision
            SourcePackage.objects.store(
                package_module,
                SPStoragePolicy(engine=engine, path=str(file_path), url="don't care", stat=stat),
                operator=bk_user,
            )

            controller = get_metadata_reader(package_module)
            assert controller.get_procfile(version_info) == expected

    @pytest.mark.parametrize("engine, archive_maker", [("TarClient", gen_tar), ("ZipClient", gen_zip)])
    @pytest.mark.parametrize(
        "contents",
        [
            ({"Procfile": "web: npm run dev\n"}),
        ],
    )
    def test_export(self, bk_user, package_module, engine, archive_maker, contents):
        version_info = VersionInfo(revision="v1", version_type="package", version_name="")
        with generate_temp_file() as file_path, generate_temp_dir() as working_dir:
            archive_maker(file_path, contents)
            controller = PackageController.init_by_module(package_module)
            stat = SourcePackageStatReader(file_path).read()
            stat.version = version_info.revision
            SourcePackage.objects.store(
                package_module,
                SPStoragePolicy(engine=engine, path=str(file_path), url="don't care", stat=stat),
                operator=bk_user,
            )

            controller.export(working_dir, version_info=version_info)
            assert {str(child.relative_to(working_dir)) for child in working_dir.iterdir()} == set(contents.keys())

    @pytest.mark.parametrize(
        "versions, expected",
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
    def test_list_alternative_versions(self, package_module, versions, expected):
        for idx, version_info in enumerate(versions):
            with generate_temp_file() as file_path:
                file_path.write_text("")
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
            expected[idx]["name"] = str(file_path.name)
            expected[idx]["extra"]["package_size"] = package.package_size
            expected[idx]["extra"]["is_deleted"] = package.is_deleted

        controller = PackageController.init_by_module(package_module)
        assert controller.list_alternative_versions() == [AlternativeVersion(**item) for item in expected]
