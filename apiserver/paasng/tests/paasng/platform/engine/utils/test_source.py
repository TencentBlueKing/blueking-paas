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

import pathlib
from typing import Any, Dict, Optional
from unittest import mock

import cattr
import pytest
import yaml
from django.test.utils import override_settings
from django_dynamic_fixture import G

from paasng.platform.declarative.constants import WEB_PROCESS
from paasng.platform.declarative.deployment.controller import DeploymentDescription
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.models.deployment import ProcessTmpl
from paasng.platform.engine.utils.output import ConsoleStream
from paasng.platform.engine.utils.source import (
    TypeProcesses,
    check_source_package,
    download_source_to_dir,
    get_source_dir,
    get_source_package_path,
)
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.exceptions import GetAppYamlError
from paasng.platform.sourcectl.models import VersionInfo
from paasng.platform.sourcectl.utils import generate_temp_dir, generate_temp_file

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def cast_to_processes(obj: Dict[str, Dict[str, Any]]) -> TypeProcesses:
    return cattr.structure(obj, TypeProcesses)


EXPECTED_WEB_PROCESS = WEB_PROCESS


class TestGetSourcePackagePath:
    """Test get_source_package_path()"""

    def test_for_svn(self, bk_module):
        deployment = Deployment.objects.create(
            region=bk_module.region,
            operator=bk_module.owner,
            app_environment=bk_module.get_envs("prod"),
            source_type=bk_module.source_type,
            source_location="svn://local-svn/app/trunk",
            source_revision="1000",
            source_version_type="trunk",
            source_version_name="trunk",
            advanced_options={},
        )
        # not use module in engine app
        assert (
            get_source_package_path(deployment)
            == f"{bk_module.region}/home/{bk_module.get_envs('prod').engine_app.name}:trunk:1000/tar"
        )

    def test_for_git(self, bk_module):
        deployment = Deployment.objects.create(
            region=bk_module.region,
            operator=bk_module.owner,
            app_environment=bk_module.get_envs("prod"),
            source_type=bk_module.source_type,
            source_location="http://git.bking.com/node-spa-demo.git",
            source_revision="6f3bfa8adf8be3",
            source_version_type="branch",
            source_version_name="dev",
            advanced_options={},
        )
        # not use module in engine app
        assert (
            get_source_package_path(deployment)
            == f"{bk_module.region}/home/{bk_module.get_envs('prod').engine_app.name}:dev:6f3bfa8adf8be3/tar"
        )


@pytest.mark.usefixtures("_init_tmpls")
class TestDownloadSourceToDir:
    """Test download_source_to_dir()"""

    @pytest.fixture(autouse=True)
    def _mocked_ctl(self):
        with (
            mock.patch("paasng.platform.engine.utils.source.get_repo_controller"),
            mock.patch("paasng.platform.engine.utils.source.PackageController"),
        ):
            yield

    def make_deploy_desc(self, bk_deployment, source_dir: str = "", processes: Optional[Dict[str, Dict]] = None):
        if processes:
            bk_deployment.update_fields(
                processes={
                    name: ProcessTmpl(name=name, command=command["command"]) for name, command in processes.items()
                }
            )

        return G(
            DeploymentDescription,
            deployment=bk_deployment,
            runtime={"source_dir": source_dir},
        )

    def test_no_patch(self, bk_module, bk_deployment):
        with generate_temp_dir() as working_dir:
            self.make_deploy_desc(bk_deployment)
            download_source_to_dir(bk_module, "user_id:100", bk_deployment, working_dir)
            assert list(working_dir.iterdir()) == []

    @pytest.mark.parametrize(
        ("source_origin", "processes", "source_dir", "target", "expected"),
        [
            (
                SourceOrigin.AUTHORIZED_VCS.value,
                {"hello": {"command": "echo 'Hello World'"}},
                "",
                "./Procfile",
                {"hello": "echo 'Hello World'"},
            ),
            # 标准应用是不会根据 deploy description 中的 source_dir 进行 patch 的
            (
                SourceOrigin.AUTHORIZED_VCS.value,
                {"hello": {"command": "echo 'Hello World'"}},
                "./foo/bar/baz",
                "./Procfile",
                {"hello": "echo 'Hello World'"},
            ),
        ],
    )
    def test_add_procfile(
        self, bk_module_full, bk_deployment_full, source_origin, processes, source_dir, target, expected
    ):
        bk_module_full.source_origin = source_origin
        with generate_temp_dir() as working_dir:
            self.make_deploy_desc(bk_deployment_full, source_dir, processes)
            download_source_to_dir(bk_module_full, "user_id:100", bk_deployment_full, working_dir)
            procfile = working_dir / target
            assert procfile.exists()
            assert procfile.is_file()
            assert yaml.safe_load(procfile.read_text()) == expected

    # 模拟 S_MART 应用的 source_dir 目录加密的场景
    def test_add_procfile_ext(self, bk_module, bk_deployment):
        bk_module.source_origin = SourceOrigin.S_MART.value
        self.make_deploy_desc(
            bk_deployment, processes={"hello": {"command": "echo 'Hello World'"}}, source_dir="./foo/bar/baz"
        )
        with generate_temp_dir() as working_dir:
            # 因为 source_dir 是文件(模拟加密目录), 所以 Procfile 注入到根目录
            (working_dir / "./foo/bar/baz").parent.mkdir(exist_ok=True, parents=True)
            (working_dir / "./foo/bar/baz").touch()
            procfile = working_dir / "./Procfile"

            download_source_to_dir(bk_module, "user_id:100", bk_deployment, working_dir)
            assert procfile.exists()
            assert procfile.is_file()
            assert yaml.safe_load(procfile.read_text()) == {"hello": "echo 'Hello World'"}


class TestCheckSourcePackage:
    """Test check_source_package()"""

    @override_settings(ENGINE_APP_SOURCE_SIZE_WARNING_THRESHOLD_MB=100)
    def test_normal(self, bk_module, capsys):
        stream = ConsoleStream()
        with generate_temp_file(suffix=".tar.gz") as package_path:
            pathlib.Path(package_path).write_text("Hello")
            check_source_package(bk_module.get_envs("prod").engine_app, package_path, stream)

            out, err = capsys.readouterr()
            assert out == ""

    @override_settings(ENGINE_APP_SOURCE_SIZE_WARNING_THRESHOLD_MB=0)
    def test_big_package(self, bk_module, capsys):
        stream = ConsoleStream()
        with generate_temp_file(suffix=".tar.gz") as package_path:
            pathlib.Path(package_path).write_text("Hello")
            check_source_package(bk_module.get_envs("prod").engine_app, package_path, stream)

            out, err = capsys.readouterr()
            assert out


class Test__get_source_dir:
    # A dummy version instance
    version_info = VersionInfo(revision="rev", version_type="tag", version_name="foo")

    def test_s_mart_desc_found(self, bk_module):
        bk_module.source_origin = SourceOrigin.S_MART
        bk_module.save()

        with mock.patch(
            "paasng.platform.engine.configurations.source_file.PackageMetaDataReader.get_app_desc",
            return_value={"spec_version": 2, "module": {"language": "python", "source_dir": "src"}},
        ):
            source_dir = get_source_dir(bk_module, "admin", self.version_info)

        assert source_dir == "src"

    def test_s_mart_desc_not_found(self, bk_module):
        bk_module.source_origin = SourceOrigin.S_MART
        bk_module.save()

        with mock.patch(
            "paasng.platform.engine.configurations.source_file.PackageMetaDataReader.get_app_desc",
            side_effect=GetAppYamlError("Not found"),
        ):
            source_dir = get_source_dir(bk_module, "admin", self.version_info)

        assert source_dir == ""
