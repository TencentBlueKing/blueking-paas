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
import pathlib
from typing import Dict, Optional
from unittest import mock

import gitlab.exceptions
import pytest
import yaml
from django.conf import settings
from django.test.utils import override_settings
from django_dynamic_fixture import G

from paasng.accounts.models import Oauth2TokenHolder, UserProfile
from paasng.dev_resources.sourcectl.exceptions import DoesNotExistsOnServer
from paasng.dev_resources.sourcectl.models import GitProject, SourcePackage
from paasng.dev_resources.sourcectl.source_types import get_sourcectl_names
from paasng.dev_resources.sourcectl.utils import generate_temp_dir, generate_temp_file
from paasng.engine.constants import DeployConditions
from paasng.engine.deploy.exceptions import DeployShouldAbortError
from paasng.engine.deploy.infras import ConsoleStream
from paasng.engine.deploy.preparations import (
    check_source_package,
    download_source_to_dir,
    get_app_description_handler,
    get_processes,
    get_processes_by_build,
    get_source_package_path,
    update_engine_app_config,
)
from paasng.engine.deploy.protections import (
    EnvProtectionCondition,
    ModuleEnvDeployInspector,
    ProductInfoCondition,
    RepoAccessCondition,
)
from paasng.engine.models import Deployment
from paasng.extensions.declarative.constants import CELERY_BEAT_PROCESS, CELERY_PROCESS, WEB_PROCESS
from paasng.extensions.declarative.deployment.controller import DeploymentDescription
from paasng.extensions.declarative.handlers import get_desc_handler
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import ApplicationMembership
from paasng.platform.core.protections.exceptions import ConditionNotMatched
from paasng.platform.environments.constants import EnvRoleOperation
from paasng.platform.environments.models import EnvRoleProtection
from paasng.platform.modules.constants import SourceOrigin
from paasng.publish.market.models import Product

pytestmark = pytest.mark.django_db


@pytest.fixture()
def git_client(bk_module):
    """A fixture used to mock Git repo dependency"""
    with mock.patch.object(bk_module, "get_source_obj"), mock.patch.object(
        GitProject, "parse_from_repo_url"
    ) as get_backends, mock.patch("paasng.dev_resources.sourcectl.controllers.gitlab.GitLabApiClient") as client:
        get_backends.return_value = GitProject(name="baz", namespace="bar", type='dft_gitlab')
        yield client()


@pytest.fixture(autouse=True)
def setup(init_tmpls, mock_current_engine_client):
    pass


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

        with mock.patch('paasng.dev_resources.sourcectl.type_specs.SvnRepoController.read_file') as mocked_read_file:
            mocked_read_file.side_effect = fake_read_file
            with pytest.raises(DeployShouldAbortError) as exc_info:
                get_processes(deployment=bk_deployment_full)

            assert error_pattern in str(exc_info)

    def test_valid_procfile_cases(self, bk_module_full, bk_deployment_full):
        def fake_read_file(key, version):
            if "Procfile" in key:
                return 'WEB: gunicorn wsgi -w 4\nworker: celery'
            raise DoesNotExistsOnServer

        with mock.patch('paasng.dev_resources.sourcectl.type_specs.SvnRepoController.read_file') as mocked_read_file:
            mocked_read_file.side_effect = fake_read_file
            processes = get_processes(bk_deployment_full)
            assert processes == {'web': 'gunicorn wsgi -w 4', 'worker': 'celery'}

    @pytest.mark.parametrize(
        'extra_info, expected',
        [
            (
                {},
                {'web': WEB_PROCESS},
            ),
            (
                {'is_use_celery': True},
                {'web': WEB_PROCESS, 'celery': CELERY_PROCESS},
            ),
            (
                {'is_use_celery': True, 'is_use_celery_beat': True},
                {'web': WEB_PROCESS, 'celery': CELERY_PROCESS, 'beat': CELERY_BEAT_PROCESS},
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
                {'web': 'start web;'},
            ),
            (
                {
                    'web': {'command': 'start web;', 'replicas': 5, 'plan': '1C2G5R'},
                    'celery': {'command': 'start celery;', 'replicas': 5},
                },
                {'web': 'start web;', 'celery': 'start celery;'},
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
                "module": {"is_default": True, "processes": {'web': {'command': 'start web'}}, "language": "python"},
            },
        )

        handler = get_app_description_handler(
            module=bk_module_full, operator=bk_module_full.owner, version_info=bk_deployment_full.version_info
        )
        assert handler is not None
        handler.handle_deployment(bk_deployment_full)

        processes = get_processes(deployment=bk_deployment_full)
        assert processes == {"web": "start web"}

    def test_get_from_deploy_config(self, bk_module_full, bk_deployment_full):
        deploy_config = bk_module_full.get_deploy_config()
        deploy_config.procfile = {"web": "start web"}
        deploy_config.save()

        processes = get_processes(deployment=bk_deployment_full)
        assert processes == {"web": "start web"}

    def test_get_from_metadata_in_package(self, bk_app_full, bk_module_full, bk_deployment_full):
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
                "module": {"is_default": True, "processes": {'web': {'command': 'start web'}}, "language": "python"},
            },
        )

        processes = get_processes(deployment=bk_deployment_full)
        assert processes == {"web": "start web"}

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

        with mock.patch('paasng.dev_resources.sourcectl.type_specs.SvnRepoController.read_file') as mocked_read_file:
            mocked_read_file.side_effect = fake_read_file

            processes = get_processes(deployment=bk_deployment_full)

        assert processes == {"web": "gunicorn wsgi -w 4", "worker": "celery"}


def test_get_processes_by_build(bk_module):
    engine_app = bk_module.envs.get(environment='prod').engine_app
    fake_build = {
        'owner': '--',
        'app': 'dbe1781d-6058-45d3-ab25-7dba160b23ac',
        'slug_path': 'ieod/home/bkapp-v20190808-001-stag:master:4017e0d6e6967a6aefdec6ae8a7898ab984e843a/push',
        'branch': 'master',
        'revision': '4017e0d6e6967a6aefdec6ae8a7898ab984e843a',
        'procfile': {
            'web': (
                'gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile - --access-logformat '
                '\'[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"\''
            )
        },
        'created': '2019-10-16T07:22:26.575317Z',
        'updated': '2019-10-16T07:22:26.575361Z',
        'uuid': 'fcd194da-70c1-4dd4-a287-441633ebbd90',
    }
    with mock.patch("paasng.engine.deploy.engine_svc.EngineDeployClient.get_build", return_value=fake_build):
        assert 'web' in get_processes_by_build(engine_app=engine_app, build_id="fake-build-id")


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


class TestDownloadSourceToDir:
    """Test download_source_to_dir()"""

    @pytest.fixture(autouse=True)
    def mocked_ctl(self):
        with mock.patch('paasng.engine.deploy.preparations.get_repo_controller'), mock.patch(
            'paasng.engine.deploy.preparations.PackageController'
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


class TestUpdateEngineAppConfig:
    """Test update_engine_app_config()"""

    def test_normal(self, bk_module, bk_deployment):
        with mock.patch('paasng.engine.deploy.preparations.EngineDeployClient') as mocked_client:
            update_engine_app_config(bk_module.get_envs("prod").engine_app, bk_deployment.version_info)
            assert mocked_client().update_config.called


class TestProductInfoCondition:
    @pytest.mark.parametrize(
        "env, create_product, ok",
        [("prod", False, False), ("prod", True, True), ("stag", False, True), ("stag", True, True)],
    )
    def test_validate(self, bk_user, bk_module, env, create_product, ok):
        application = bk_module.application
        env = bk_module.get_envs(env)

        if create_product:
            G(Product, application=application)

        if ok:
            ProductInfoCondition(bk_user, env).validate()
        else:
            with pytest.raises(ConditionNotMatched) as exc_info:
                ProductInfoCondition(bk_user, env).validate()

            assert exc_info.value.action_name == DeployConditions.FILL_PRODUCT_INFO.value


class TestEnvProtectionCondition:
    @pytest.mark.parametrize(
        "user_role, allowed_roles, ok",
        [
            (ApplicationRole.ADMINISTRATOR, [], True),
            (ApplicationRole.ADMINISTRATOR, [ApplicationRole.ADMINISTRATOR], True),
            (ApplicationRole.ADMINISTRATOR, [ApplicationRole.DEVELOPER], False),
            (ApplicationRole.DEVELOPER, [], True),
            (ApplicationRole.DEVELOPER, [ApplicationRole.ADMINISTRATOR], False),
            (ApplicationRole.DEVELOPER, [ApplicationRole.DEVELOPER], True),
            (ApplicationRole.DEVELOPER, [ApplicationRole.ADMINISTRATOR, ApplicationRole.DEVELOPER], True),
        ],
    )
    def test_validate(self, bk_user, bk_module, user_role, allowed_roles, ok):
        application = bk_module.application
        env = bk_module.get_envs("stag")
        ApplicationMembership.objects.filter(application=application, user=bk_user.pk).update(role=user_role.value)

        for role in allowed_roles:
            EnvRoleProtection.objects.create(
                allowed_role=role.value, module_env=env, operation=EnvRoleOperation.DEPLOY.value
            )

        if ok:
            EnvProtectionCondition(bk_user, env).validate()
        else:
            with pytest.raises(ConditionNotMatched):
                EnvProtectionCondition(bk_user, env).validate()
            inspector = ModuleEnvDeployInspector(bk_user, env)
            inspector.conditions = [EnvProtectionCondition(bk_user, env)]
            assert [item.action_name for item in inspector.perform().failed_conditions] == [
                EnvProtectionCondition.action_name
            ]


class TestRepoAccessCondition:
    @pytest.mark.parametrize(
        "source_type, create_user_profile, create_token_holder, ok, action_name",
        [
            ('dft_gitlab', False, False, False, DeployConditions.NEED_TO_BIND_OAUTH_INFO),
            ('dft_gitlab', True, False, False, DeployConditions.NEED_TO_BIND_OAUTH_INFO),
            ('dft_gitlab', True, True, False, DeployConditions.DONT_HAVE_ENOUGH_PERMISSIONS),
            ('dft_gitlab', True, True, True, ...),
        ],
    )
    def test_validate(
        self, bk_user, bk_module, git_client, source_type, create_user_profile, create_token_holder, ok, action_name
    ):
        env = bk_module.get_envs("stag")
        bk_module.source_type = source_type
        bk_module.save()
        if create_user_profile:
            profile = G(UserProfile, user=bk_user)
            if create_token_holder:
                G(Oauth2TokenHolder, user=profile, provider=get_sourcectl_names().GitLab)

        if ok:
            assert RepoAccessCondition(bk_user, env).validate() is None
        else:

            def get_project_info(project):
                raise gitlab.exceptions.GitlabAuthenticationError

            git_client.get_project_info.side_effect = get_project_info
            with pytest.raises(ConditionNotMatched) as exc_info:
                RepoAccessCondition(bk_user, env).validate()

            assert exc_info.value.action_name == action_name.value
            inspector = ModuleEnvDeployInspector(bk_user, env)
            inspector.conditions = [RepoAccessCondition(bk_user, env)]
            assert [item.action_name for item in inspector.perform().failed_conditions] == [action_name.value]


class TestModuleEnvDeployInspector:
    @pytest.mark.parametrize(
        "user_role, allowed_roles, create_token, create_product, expected",
        [
            (
                ApplicationRole.DEVELOPER,
                [ApplicationRole.ADMINISTRATOR],
                False,
                False,
                [
                    DeployConditions.FILL_PRODUCT_INFO,
                    DeployConditions.CHECK_ENV_PROTECTION,
                    DeployConditions.NEED_TO_BIND_OAUTH_INFO,
                ],
            ),
            (
                ApplicationRole.OPERATOR,
                [ApplicationRole.ADMINISTRATOR],
                True,
                False,
                [DeployConditions.FILL_PRODUCT_INFO, DeployConditions.CHECK_ENV_PROTECTION],
            ),
            (
                ApplicationRole.ADMINISTRATOR,
                ...,
                True,
                False,
                [DeployConditions.FILL_PRODUCT_INFO],
            ),
            (
                ...,
                ...,
                True,
                True,
                [],
            ),
        ],
    )
    def test(self, bk_user, bk_module, git_client, user_role, allowed_roles, create_token, create_product, expected):
        application = bk_module.application
        env = bk_module.get_envs("prod")
        bk_module.source_type = get_sourcectl_names().GitLab
        bk_module.save()

        if user_role is not ...:
            ApplicationMembership.objects.filter(application=application, user=bk_user.pk).update(role=user_role.value)

        if allowed_roles is not ...:
            for role in allowed_roles:
                EnvRoleProtection.objects.create(
                    allowed_role=role.value, module_env=env, operation=EnvRoleOperation.DEPLOY.value
                )

        if create_token:
            profile = G(UserProfile, user=bk_user)
            G(Oauth2TokenHolder, user=profile, provider=get_sourcectl_names().GitLab)

        if create_product:
            G(Product, application=application)

        inspector = ModuleEnvDeployInspector(bk_user, env)
        assert [item.action_name for item in inspector.perform().failed_conditions] == [c.value for c in expected]
        assert inspector.all_matched is not len(expected)
