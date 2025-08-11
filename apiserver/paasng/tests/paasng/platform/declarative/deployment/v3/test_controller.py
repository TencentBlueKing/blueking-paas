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

from pathlib import Path

import cattr
import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities import Component
from paasng.platform.bkapp_model.entities import DomainResolution as DomainResolutionEntity
from paasng.platform.bkapp_model.entities.hooks import HookCmd, Hooks
from paasng.platform.bkapp_model.entities.svc_discovery import SvcDiscEntryBkSaaS
from paasng.platform.bkapp_model.entities_syncer.domain_resolution import sync_domain_resolution
from paasng.platform.bkapp_model.entities_syncer.hooks import sync_hooks
from paasng.platform.bkapp_model.entities_syncer.svc_discovery import sync_svc_discovery
from paasng.platform.bkapp_model.models import (
    DomainResolution,
    ModuleProcessSpec,
    SvcDiscConfig,
    get_svc_disc_as_env_variables,
)
from paasng.platform.declarative.deployment.controller import DeploymentDeclarativeController
from paasng.platform.declarative.deployment.svc_disc import BkSaaSEnvVariableFactory
from paasng.platform.declarative.deployment.validations.v3 import DeploymentDescSLZ
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.declarative.serializers import validate_desc
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models import Module
from paasng.platform.modules.models.deploy_config import Hook, HookList
from tests.paasng.platform.declarative.utils import AppDescV3Builder as builder  # noqa: N813
from tests.utils.mocks.cluster import cluster_ingress_config

pytestmark = [pytest.mark.django_db(databases=["default", "workloads"]), pytest.mark.usefixtures("bk_cnative_app")]


class TestProcessesField:
    @pytest.fixture(autouse=True)
    def _mock_components_dir(self, monkeypatch):
        test_dir = Path(settings.BASE_DIR) / "tests" / "support-files" / "test_components"
        monkeypatch.setattr("paasng.accessories.proc_components.manager.DEFAULT_COMPONENT_DIR", test_dir)

    def test_python_framework_case(self, bk_module, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "processes": [
                    {
                        "name": "web",
                        "command": ["gunicorn"],
                        "args": [
                            "wsgi",
                            "-w",
                            "4",
                            "-b",
                            "[::]:${PORT:-5000}",
                            "--access-logfile",
                            "-",
                            "--error-logfile",
                            "-",
                            "--access-logformat",
                            '[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"',
                        ],
                        "replicas": 1,
                        "components": [
                            {
                                "name": "test_env_overlay",
                                "version": "v1",
                                "properties": {
                                    "env": [{"name": "proc_name", "value": "FOO"}, {"name": "key", "value": "1"}]
                                },
                            },
                        ],
                    }
                ]
            },
        )

        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        web = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert (
            web.get_proc_command()
            == 'gunicorn wsgi -w 4 -b [::]:${PORT} --access-logfile - --error-logfile - --access-logformat \'[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"\''
        )
        assert (
            bk_deployment.declarative_config.spec.processes[0].get_proc_command()
            == 'bash -c \'"$(eval echo \\"$0\\")" "$(eval echo \\"${1}\\")" "$(eval echo \\"${2}\\")" "$(eval echo \\"${3}\\")" "$(eval echo \\"${4}\\")" "$(eval echo \\"${5}\\")" "$(eval echo \\"${6}\\")" "$(eval echo \\"${7}\\")" "$(eval echo \\"${8}\\")" "$(eval echo \\"${9}\\")" "$(eval echo \\"${10}\\")" "$(eval echo \\"${11}\\")"\' gunicorn wsgi -w 4 -b \'[::]:${PORT:-5000}\' --access-logfile - --error-logfile - --access-logformat \'[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"\''
        )
        assert web.components == [
            Component(
                name="test_env_overlay",
                version="v1",
                properties={"env": [{"name": "proc_name", "value": "FOO"}, {"name": "key", "value": "1"}]},
            ),
        ]

    def test_proc_component_not_exists(self, bk_module, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "processes": [
                    {
                        "name": "web",
                        "command": ["gunicorn"],
                        "replicas": 1,
                        "components": [
                            {
                                "name": "not_exists",
                                "version": "v1",
                                "properties": {"envs": [{"proc_name": "FOO", "value": "1"}]},
                            },
                        ],
                    }
                ]
            },
        )

        controller = DeploymentDeclarativeController(bk_deployment)
        with pytest.raises(
            DescriptionValidationError, match="spec.processes.0.components.0: 组件 not_exists-v1 不存在"
        ):
            controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

    def test_proc_component_with_invalid_properties(self, bk_module, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "processes": [
                    {
                        "name": "web",
                        "command": ["gunicorn"],
                        "replicas": 1,
                        "components": [
                            {
                                "name": "test_env_overlay",
                                "version": "v1",
                                "properties": {"envs": [{"procXX": "FOO", "value": "1"}]},
                            },
                        ],
                    }
                ]
            },
        )

        controller = DeploymentDeclarativeController(bk_deployment)
        with pytest.raises(DescriptionValidationError, match="spec.processes.0.components.0: 参数校验失败"):
            controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))


class TestEnvVariablesField:
    def test_invalid_input(self, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "configuration": {"env": ""},
                "envOverlay": {
                    "envVariables": [
                        {"name": "BAZ", "value": "stag", "envName": "stag"},
                        {"name": "BAZ", "value": "prod", "envName": "prod"},
                    ]
                },
                "processes": [],
            },
        )
        controller = DeploymentDeclarativeController(bk_deployment)
        with pytest.raises(DescriptionValidationError, match="spec.configuration.env"):
            controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

    def test_preset_environ_vars(self, bk_module, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "configuration": {"env": [{"name": "FOO", "value": "1"}, {"name": "BAR", "value": "2"}]},
                "envOverlay": {
                    "envVariables": [
                        {"name": "BAZ", "value": "stag", "envName": "stag"},
                        {"name": "BAZ", "value": "prod", "envName": "prod"},
                    ]
                },
                "processes": [],
            },
        )
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert PresetEnvVariable.objects.filter(module=bk_module).count() == 4
        assert (
            PresetEnvVariable.objects.filter(module=bk_module, environment_name=ConfigVarEnvName.GLOBAL).count() == 2
        )
        assert (
            PresetEnvVariable.objects.filter(module=bk_module, environment_name=ConfigVarEnvName.STAG).get().value
            == "stag"
        )
        assert (
            PresetEnvVariable.objects.filter(module=bk_module, environment_name=ConfigVarEnvName.PROD).get().value
            == "prod"
        )


class TestSvcDiscoveryField:
    @staticmethod
    def apply_config(bk_deployment):
        G(Application, code="foo-app", region=settings.DEFAULT_REGION_NAME)
        app = G(Application, code="bar-app", region=settings.DEFAULT_REGION_NAME)
        G(Module, name="api", application=app)

        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "svcDiscovery": {"bkSaaS": [{"bkAppCode": "foo-app"}, {"bkAppCode": "bar-app", "moduleName": "api"}]},
                "processes": [],
            },
        )
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

    def test_as_env_vars_domain(self, bk_deployment):
        with cluster_ingress_config(replaced_config={"app_root_domains": [{"name": "foo.com"}, {"name": "bar.com"}]}):
            self.apply_config(bk_deployment)
            env_vars = get_svc_disc_as_env_variables(bk_deployment.app_environment)
            value = env_vars["BKPAAS_SERVICE_ADDRESSES_BKSAAS"]
            addresses = BkSaaSEnvVariableFactory.decode_data(value)
            assert len(addresses) == 2
            assert addresses[0]["key"] == {"bk_app_code": "foo-app", "module_name": None}
            assert addresses[0]["value"] == {
                "stag": "http://stag-dot-foo-app.foo.com",
                "prod": "http://foo-app.foo.com",
            }

            assert addresses[1]["key"] == {"bk_app_code": "bar-app", "module_name": "api"}
            assert addresses[1]["value"] == {
                "stag": "http://stag-dot-api-dot-bar-app.foo.com",
                "prod": "http://prod-dot-api-dot-bar-app.foo.com",
            }

    def test_as_env_vars_subpath(self, bk_deployment):
        with cluster_ingress_config(replaced_config={"sub_path_domains": [{"name": "foo.com"}, {"name": "bar.com"}]}):
            self.apply_config(bk_deployment)
            env_vars = get_svc_disc_as_env_variables(bk_deployment.app_environment)
            value = env_vars["BKPAAS_SERVICE_ADDRESSES_BKSAAS"]
            addresses = BkSaaSEnvVariableFactory.decode_data(value)
            assert len(addresses) == 2
            assert addresses[0]["key"] == {"bk_app_code": "foo-app", "module_name": None}
            assert addresses[0]["value"] == {
                "stag": "http://foo.com/stag--foo-app/",
                "prod": "http://foo.com/foo-app/",
            }

            assert addresses[1]["key"] == {"bk_app_code": "bar-app", "module_name": "api"}
            assert addresses[1]["value"] == {
                "stag": "http://foo.com/stag--api--bar-app/",
                "prod": "http://foo.com/prod--api--bar-app/",
            }


class TestSvcDiscoveryFieldMultiManagers:
    def test_notset_should_reset(self, bk_cnative_app, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={
                "svcDiscovery": {"bkSaaS": [{"bkAppCode": bk_cnative_app.code}]},
                "processes": [],
            },
        )
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        assert len(SvcDiscConfig.objects.get(application=bk_cnative_app).bk_saas) == 1

        # Re-apply the data without svc_discovery
        json_data = builder.make_module(module_name="test", module_spec={"processes": []})
        perform_action(bk_deployment, json_data)
        assert not SvcDiscConfig.objects.filter(application=bk_cnative_app).exists()

    def test_notset_should_skip_when_manager_different(self, bk_cnative_app, bk_module, bk_deployment):
        # Insert the data using "web_form" manager
        sync_svc_discovery(
            bk_module,
            SvcDiscConfig(bk_saas=[SvcDiscEntryBkSaaS(bk_app_code=bk_cnative_app.code)]),
            fieldmgr.FieldMgrName.WEB_FORM,
        )
        assert len(SvcDiscConfig.objects.get(application=bk_cnative_app).bk_saas) == 1

        # Re-apply the data without svc_discovery, the data should stay because it's
        # managed by a different manager.
        json_data = builder.make_module(module_name="test", module_spec={"processes": []})
        perform_action(bk_deployment, json_data)
        assert len(SvcDiscConfig.objects.get(application=bk_cnative_app).bk_saas) == 1


class TestHookField:
    def test_field_not_set(self, bk_module, bk_deployment):
        controller = DeploymentDeclarativeController(bk_deployment)
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, builder.make_module(module_name="test")))

        assert len(bk_deployment.get_deploy_hooks()) == 0
        self.assert_hook_not_exist(bk_module, bk_deployment)

    def test_field_set(self, bk_module, bk_deployment):
        controller = DeploymentDeclarativeController(bk_deployment)
        json_data = builder.make_module(
            module_name="test",
            module_spec={"hooks": {"preRelease": {"command": [], "args": ["echo", "1"]}}, "processes": []},
        )
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        self.assert_one_hook_with_command(bk_module, bk_deployment, [], ["echo", "1"])

    @pytest.mark.parametrize("hook_disabled", [True, False])
    def test_not_set_should_not_touch_deployment(self, hook_disabled, bk_module, bk_deployment):
        bk_module.deploy_hooks.enable_hook(DeployHookType.PRE_RELEASE_HOOK, command=[], args=["echo", "1"])

        # 设置 hook 被 web_form 管理
        fieldmgr.FieldManager(bk_module, fieldmgr.F_HOOKS).set(fieldmgr.FieldMgrName.WEB_FORM)

        if hook_disabled:
            bk_module.deploy_hooks.disable_hook(DeployHookType.PRE_RELEASE_HOOK)

        controller = DeploymentDeclarativeController(bk_deployment)

        json_data = builder.make_module(module_name="test", module_spec={"processes": []})
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        deploy_hooks = bk_deployment.get_deploy_hooks()
        if hook_disabled:
            assert len(deploy_hooks) == 0
        else:
            assert len(deploy_hooks) == 1
            assert deploy_hooks[0].args == ["echo", "1"]

        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert desc_obj.get_deploy_hooks() == HookList()

    @pytest.mark.parametrize("hook_disabled", [True, False])
    def test_rewrite_the_hook(self, hook_disabled, bk_module, bk_deployment):
        bk_module.deploy_hooks.enable_hook(DeployHookType.PRE_RELEASE_HOOK, command=[], args=["echo", "1"])
        if hook_disabled:
            bk_module.deploy_hooks.disable_hook(DeployHookType.PRE_RELEASE_HOOK)

        controller = DeploymentDeclarativeController(bk_deployment)

        json_data = builder.make_module(
            module_name="test",
            module_spec={"hooks": {"preRelease": {"command": [], "args": ["echo", "2"]}}, "processes": []},
        )
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        self.assert_one_hook_with_command(bk_module, bk_deployment, [], ["echo", "2"])

    def test_not_set_should_reset(self, bk_module, bk_deployment):
        controller = DeploymentDeclarativeController(bk_deployment)

        json_data = builder.make_module(
            module_name="test",
            module_spec={"hooks": {"preRelease": {"command": [], "args": ["echo", "1"]}}, "processes": []},
        )
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))
        self.assert_one_hook_with_command(bk_module, bk_deployment, [], ["echo", "1"])

        json_data = builder.make_module(module_name="test", module_spec={"processes": []})
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))
        self.assert_hook_not_exist(bk_module, bk_deployment)

    def test_not_set_with_different_mgr_should_keep(self, bk_module, bk_deployment):
        sync_hooks(
            bk_module,
            Hooks(pre_release=HookCmd(command=["echo"])),
            fieldmgr.FieldMgrName.WEB_FORM,
        )
        module_hook = bk_module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        assert module_hook.command == ["echo"]

        controller = DeploymentDeclarativeController(bk_deployment)
        json_data = builder.make_module(module_name="test", module_spec={"processes": []})
        controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))

        module_hook = bk_module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        assert module_hook.command == ["echo"]

    # Helper methods start

    def assert_hook_not_exist(self, module, deployment):
        desc_obj = DeploymentDescription.objects.get(deployment=deployment)
        assert desc_obj.get_deploy_hooks() == HookList()
        module_hook = module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        assert module_hook is None

    def assert_one_hook_with_command(self, module, deployment, command, args):
        desc_obj = DeploymentDescription.objects.get(deployment=deployment)

        hook_list = HookList([cattr.structure({"type": "pre-release-hook", "command": command, "args": args}, Hook)])
        assert desc_obj.get_deploy_hooks() == hook_list
        assert deployment.get_deploy_hooks() == hook_list

        module_hook = module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        assert module_hook.command == command
        assert module_hook.args == args


class TestDomainResolutionFieldMultiManagers:
    def test_notset_should_reset(self, bk_cnative_app, bk_deployment):
        json_data = builder.make_module(
            module_name="test",
            module_spec={"domainResolution": {"nameservers": ["8.8.8.8"]}, "processes": []},
        )
        perform_action(bk_deployment, json_data)
        assert len(DomainResolution.objects.get(application=bk_cnative_app).nameservers) == 1

        # Re-apply the data without svc_discovery
        json_data = builder.make_module(module_name="test", module_spec={"processes": []})
        perform_action(bk_deployment, json_data)
        assert not DomainResolution.objects.filter(application=bk_cnative_app).exists()

    def test_notset_should_skip_when_manager_different(self, bk_cnative_app, bk_module, bk_deployment):
        # Insert the data using "web_form" manager
        sync_domain_resolution(
            bk_module,
            DomainResolutionEntity(nameservers=["8.8.8.8"], host_aliases=[]),
            fieldmgr.FieldMgrName.WEB_FORM,
        )
        assert len(DomainResolution.objects.get(application=bk_cnative_app).nameservers) == 1

        # Re-apply the data without svc_discovery, the data should stay because it's
        # managed by a different manager.
        json_data = builder.make_module(module_name="test", module_spec={"processes": []})
        perform_action(bk_deployment, json_data)
        assert len(DomainResolution.objects.get(application=bk_cnative_app).nameservers) == 1


def perform_action(deployment: Deployment, json_data: dict):
    """A shortcut to perform validation and action on a deployment using the given data."""
    controller = DeploymentDeclarativeController(deployment)
    controller.perform_action(desc=validate_desc(DeploymentDescSLZ, json_data))


def test_default_app_with_ver_3(bk_cnative_app, bk_module, bk_deployment):
    bk_cnative_app.type = ApplicationType.DEFAULT
    bk_cnative_app.save()

    controller = DeploymentDeclarativeController(bk_deployment)
    with pytest.raises(DescriptionValidationError):
        controller.perform_action(
            desc=validate_desc(
                DeploymentDescSLZ, builder.make_module(module_name="test", module_spec={"processes": []})
            )
        )
