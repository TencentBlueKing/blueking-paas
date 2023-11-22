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
import pathlib
from typing import Any, Dict, Optional
from unittest import mock

import cattr
import pytest
import yaml
from django.conf import settings
from django.test.utils import override_settings
from django_dynamic_fixture import G

from paasng.platform.declarative.constants import CELERY_BEAT_PROCESS, CELERY_PROCESS, WEB_PROCESS
from paasng.platform.declarative.deployment.controller import DeploymentDescription
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.engine.exceptions import DeployShouldAbortError
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.utils.output import ConsoleStream
from paasng.platform.engine.utils.source import (
    TypeProcesses,
    check_source_package,
    download_source_to_dir,
    get_app_description_handler,
    get_processes,
    get_source_package_path,
)
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.exceptions import DoesNotExistsOnServer
from paasng.platform.sourcectl.models import SourcePackage
from paasng.platform.sourcectl.utils import generate_temp_dir, generate_temp_file

pytestmark = pytest.mark.django_db


def cast_to_processes(obj: Dict[str, Dict[str, Any]]) -> TypeProcesses:
    return cattr.structure(obj, TypeProcesses)


@pytest.mark.usefixtures("init_tmpls")
class TestGetProcesses:
    """Test get_procfile()"""

    @pytest.mark.parametrize(
        'file_content,error_pattern',
        [
            (ValueError("trivial value error"), 'Can not read Procfile file from repository'),
            ('invalid#$type: gunicorn\n', 'pattern'),
            ('{}: gunicorn\n'.format('p' * 13), 'longer than'),
        ],
    )
    def test_invalid_procfile_cases(self, file_content, error_pattern, bk_module_full, bk_deployment_full):
        def fake_read_file(key, version):
            if "Procfile" in key:
                if isinstance(file_content, Exception):
                    raise file_content
                return file_content
            raise DoesNotExistsOnServer

        with mock.patch('paasng.platform.sourcectl.type_specs.SvnRepoController.read_file') as mocked_read_file:
            mocked_read_file.side_effect = fake_read_file
            with pytest.raises(DeployShouldAbortError) as exc_info:
                get_processes(deployment=bk_deployment_full)

            assert error_pattern in str(exc_info)

    def test_valid_procfile_cases(self, bk_module_full, bk_deployment_full):
        def fake_read_file(key, version):
            if "Procfile" in key:
                return 'WEB: gunicorn wsgi -w 4\nworker: celery'
            raise DoesNotExistsOnServer

        with mock.patch('paasng.platform.sourcectl.type_specs.SvnRepoController.read_file') as mocked_read_file:
            mocked_read_file.side_effect = fake_read_file
            processes = get_processes(bk_deployment_full)
            assert processes == cast_to_processes(
                {
                    "web": {"name": "web", "command": "gunicorn wsgi -w 4"},
                    "worker": {"name": "worker", "command": "celery"},
                }
            )

    @pytest.mark.parametrize(
        'extra_info, expected',
        [
            (
                {},
                cast_to_processes({"web": {"name": "web", "command": WEB_PROCESS}}),
            ),
            (
                {'is_use_celery': True},
                cast_to_processes(
                    {
                        "web": {"name": "web", "command": WEB_PROCESS},
                        "celery": {"name": "celery", "command": CELERY_PROCESS},
                    }
                ),
            ),
            (
                {'is_use_celery': True, 'is_use_celery_beat': True},
                cast_to_processes(
                    {
                        "web": {
                            "name": "web",
                            "command": WEB_PROCESS,
                        },
                        "celery": {
                            "name": "celery",
                            "command": CELERY_PROCESS,
                        },
                        "beat": {"name": "beat", "command": CELERY_BEAT_PROCESS},
                    }
                ),
            ),
        ],
    )
    def test_v1_app_desc_cases(self, extra_info, expected, bk_app_full, bk_module_full, bk_deployment_full):
        app_desc = {
            'app_code': bk_app_full.code,
            'app_name': bk_app_full.name,
            'author': 'blueking',
            'introduction': 'blueking app',
            'is_use_celery': False,
            'version': '0.0.1',
            'env': [],
            **extra_info,
        }
        get_desc_handler(app_desc).handle_deployment(bk_deployment_full)
        processes = get_processes(deployment=bk_deployment_full)
        assert processes == expected

    @pytest.mark.parametrize(
        'processes_desc, expected',
        [
            (
                {'web': {'command': 'start web;'}},
                cast_to_processes({'web': {'name': 'web', 'command': 'start web;'}}),
            ),
            (
                {
                    'web': {'command': 'start web;', 'replicas': 5, 'plan': '1C2G5R'},
                    'celery': {'command': 'start celery;', 'replicas': 5},
                },
                cast_to_processes(
                    {
                        'web': {'name': 'web', 'command': 'start web;', 'replicas': 5, 'plan': '1C2G5R'},
                        'celery': {'name': 'celery', 'command': 'start celery;', 'replicas': 5},
                    }
                ),
            ),
        ],
    )
    def test_v2_app_desc_cases(self, processes_desc, expected, bk_app_full, bk_module_full, bk_deployment_full):
        app_desc = {
            'spec_version': 2,
            'region': settings.DEFAULT_REGION_NAME,
            'bk_app_code': bk_app_full.code,
            'bk_app_name': bk_app_full.name,
            "market": {"introduction": "应用简介", "display_options": {"open_mode": "desktop"}},
            "module": {"is_default": True, "processes": processes_desc, "language": "python"},
        }
        get_desc_handler(app_desc).handle_deployment(bk_deployment_full)
        processes = get_processes(deployment=bk_deployment_full)
        assert processes == expected

    def test_metadata_in_package(self, bk_app_full, bk_module_full, bk_deployment_full):
        """s-mart case: 当处理 app_desc 后, 从源码包读取进程包含进程启动命令、方案、副本数等信息"""
        bk_module_full.source_origin = SourceOrigin.S_MART
        bk_module_full.save()

        G(
            SourcePackage,
            module=bk_module_full,
            version=bk_deployment_full.version_info.revision,
            meta_info={
                'spec_version': 2,
                'region': settings.DEFAULT_REGION_NAME,
                'bk_app_code': bk_app_full.code,
                'bk_app_name': bk_app_full.name,
                "market": {"introduction": "应用简介", "display_options": {"open_mode": "desktop"}},
                "module": {
                    "is_default": True,
                    "processes": {'web': {'command': 'start web', 'plan': 'default', 'replicas': 5}},
                    "language": "python",
                },
            },
        )

        handler = get_app_description_handler(
            module=bk_module_full, operator=bk_module_full.owner, version_info=bk_deployment_full.version_info
        )
        assert handler is not None
        handler.handle_deployment(bk_deployment_full)

        processes = get_processes(deployment=bk_deployment_full)
        assert processes == cast_to_processes(
            {'web': {'name': 'web', 'command': 'start web', 'plan': 'default', 'replicas': 5}}
        )

    def test_get_from_metadata_in_package(self, bk_app_full, bk_module_full, bk_deployment_full):
        """s-mart case: 当未处理 app_desc 时, 从源码包读取进程仅包含进程启动命令信息"""
        bk_module_full.source_origin = SourceOrigin.S_MART
        bk_module_full.save()

        G(
            SourcePackage,
            module=bk_module_full,
            version=bk_deployment_full.version_info.revision,
            meta_info={
                'spec_version': 2,
                'region': settings.DEFAULT_REGION_NAME,
                'bk_app_code': bk_app_full.code,
                'bk_app_name': bk_app_full.name,
                "market": {"introduction": "应用简介", "display_options": {"open_mode": "desktop"}},
                "module": {
                    "is_default": True,
                    "processes": {'web': {'command': 'start web', 'plan': 'default'}},
                    "language": "python",
                },
            },
        )

        processes = get_processes(deployment=bk_deployment_full)
        assert processes == cast_to_processes({'web': {'name': 'web', 'command': 'start web'}})

    def test_both_app_description_and_procfile(self, bk_app_full, bk_module_full, bk_deployment_full):
        """应用描述文件和 Procfile 同时定义, 以 Procfile 为准"""
        app_desc = {
            'spec_version': 2,
            'region': settings.DEFAULT_REGION_NAME,
            'bk_app_code': bk_app_full.code,
            'bk_app_name': bk_app_full.name,
            "market": {"introduction": "应用简介", "display_options": {"open_mode": "desktop"}},
            "module": {
                "is_default": True,
                "processes": {"web": {"command": "gunicorn wsgi -w 4"}},
                "language": "python",
            },
        }
        get_desc_handler(app_desc).handle_deployment(bk_deployment_full)

        def fake_read_file(key, version):
            if "Procfile" in key:
                return 'WEB: gunicorn wsgi -w 4\nworker: celery'
            raise DoesNotExistsOnServer

        with mock.patch('paasng.platform.sourcectl.type_specs.SvnRepoController.read_file') as mocked_read_file:
            mocked_read_file.side_effect = fake_read_file

            processes = get_processes(deployment=bk_deployment_full)

        assert processes == cast_to_processes(
            {
                'web': {'name': 'web', 'command': 'gunicorn wsgi -w 4'},
                'worker': {'name': 'worker', 'command': 'celery'},
            }
        )


class TestGetSourcePackagePath:
    """Test get_source_package_path()"""

    def test_for_svn(self, bk_module):
        deployment = Deployment.objects.create(
            region=bk_module.region,
            operator=bk_module.owner,
            app_environment=bk_module.get_envs('prod'),
            source_type=bk_module.source_type,
            source_location='svn://local-svn/app/trunk',
            source_revision='1000',
            source_version_type='trunk',
            source_version_name='trunk',
            advanced_options={},
        )
        # not use module in engine app
        assert (
            get_source_package_path(deployment)
            == f'{bk_module.region}/home/{bk_module.get_envs("prod").engine_app.name}:trunk:1000/tar'
        )

    def test_for_git(self, bk_module):
        deployment = Deployment.objects.create(
            region=bk_module.region,
            operator=bk_module.owner,
            app_environment=bk_module.get_envs('prod'),
            source_type=bk_module.source_type,
            source_location='http://git.bking.com/node-spa-demo.git',
            source_revision='6f3bfa8adf8be3',
            source_version_type='branch',
            source_version_name='dev',
            advanced_options={},
        )
        # not use module in engine app
        assert (
            get_source_package_path(deployment)
            == f'{bk_module.region}/home/{bk_module.get_envs("prod").engine_app.name}:dev:6f3bfa8adf8be3/tar'
        )


@pytest.mark.usefixtures("init_tmpls")
class TestDownloadSourceToDir:
    """Test download_source_to_dir()"""

    @pytest.fixture(autouse=True)
    def mocked_ctl(self):
        with mock.patch('paasng.platform.engine.utils.source.get_repo_controller'), mock.patch(
            'paasng.platform.engine.utils.source.PackageController'
        ):
            yield

    def make_deploy_desc(self, bk_deployment, source_dir: str = "", processes: Optional[Dict[str, Dict]] = None):
        return G(
            DeploymentDescription,
            deployment=bk_deployment,
            runtime={"processes": processes or {}, "source_dir": source_dir},
        )

    def test_no_patch(self, bk_module, bk_deployment):
        with generate_temp_dir() as working_dir:
            self.make_deploy_desc(bk_deployment)
            download_source_to_dir(bk_module, 'user_id:100', bk_deployment, working_dir)
            assert list(working_dir.iterdir()) == []

    @pytest.mark.parametrize(
        "source_origin, processes, source_dir, target, expected",
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
            download_source_to_dir(bk_module_full, 'user_id:100', bk_deployment_full, working_dir)
            procfile = working_dir / target
            assert procfile.exists()
            assert procfile.is_file()
            assert yaml.load(procfile.read_text()) == expected

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

            download_source_to_dir(bk_module, 'user_id:100', bk_deployment, working_dir)
            assert procfile.exists()
            assert procfile.is_file()
            assert yaml.load(procfile.read_text()) == {"hello": "echo 'Hello World'"}


class TestCheckSourcePackage:
    """Test check_source_package()"""

    @override_settings(ENGINE_APP_SOURCE_SIZE_WARNING_THRESHOLD_MB=100)
    def test_normal(self, bk_module, capsys):
        stream = ConsoleStream()
        with generate_temp_file(suffix='.tar.gz') as package_path:
            pathlib.Path(package_path).write_text("Hello")
            check_source_package(bk_module.get_envs("prod").engine_app, package_path, stream)

            out, err = capsys.readouterr()
            assert out == ''

    @override_settings(ENGINE_APP_SOURCE_SIZE_WARNING_THRESHOLD_MB=0)
    def test_big_package(self, bk_module, capsys):
        stream = ConsoleStream()
        with generate_temp_file(suffix='.tar.gz') as package_path:
            pathlib.Path(package_path).write_text("Hello")
            check_source_package(bk_module.get_envs("prod").engine_app, package_path, stream)

            out, err = capsys.readouterr()
            assert out
