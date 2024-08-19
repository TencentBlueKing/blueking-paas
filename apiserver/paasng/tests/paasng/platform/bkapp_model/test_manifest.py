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

import functools
from unittest import mock

import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paas_wl.bk_app.cnative.specs.constants import ApiVersion, MountEnvName, VolumeSourceType
from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.cnative.specs.crd.metadata import ObjectMetadata
from paas_wl.bk_app.cnative.specs.models import Mount
from paas_wl.bk_app.processes.models import initialize_default_proc_spec_plans
from paas_wl.core.resource import generate_bkapp_name
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.platform.bkapp_model.constants import ResQuotaPlan
from paasng.platform.bkapp_model.manifest import (
    DEFAULT_SLUG_RUNNER_ENTRYPOINT,
    AddonsManifestConstructor,
    BuiltinAnnotsManifestConstructor,
    DomainResolutionManifestConstructor,
    EnvVarsManifestConstructor,
    HooksManifestConstructor,
    MountsManifestConstructor,
    ProcessesManifestConstructor,
    SvcDiscoveryManifestConstructor,
    apply_builtin_env_vars,
    apply_env_annots,
    get_manifest,
)
from paasng.platform.bkapp_model.models import (
    DomainResolution,
    ModuleProcessSpec,
    ProcessSpecEnvOverlay,
    SvcDiscConfig,
)
from paasng.platform.declarative.deployment.controller import DeploymentDescription
from paasng.platform.engine.constants import ConfigVarEnvName, RuntimeType
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.engine.models.deployment import ProcService
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models import BuildConfig
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def blank_resource() -> crd.BkAppResource:
    """A blank resource object."""
    return crd.BkAppResource(
        apiVersion=ApiVersion.V1ALPHA2, metadata=ObjectMetadata(name="a-blank-resource"), spec=crd.BkAppSpec()
    )


@pytest.fixture()
def local_service(bk_app):
    """A local service object."""
    service = G(Service, name="mysql", category=G(ServiceCategory), region=bk_app.region, logo_b64="dummy")
    _ = G(Plan, name=generate_random_string(), service=service)
    return mixed_service_mgr.get(service.uuid, region=bk_app.region)


@pytest.fixture()
def process_web(bk_module) -> ModuleProcessSpec:
    """ProcessSpec for web"""
    return G(ModuleProcessSpec, module=bk_module, name="web", proc_command="python -m http.server", port=8000)


@pytest.fixture()
def process_web_overlay(process_web) -> ProcessSpecEnvOverlay:
    """An overlay data for web process"""
    return G(
        ProcessSpecEnvOverlay,
        proc_spec=process_web,
        environment_name="stag",
        target_replicas=10,
        plan_name="Starter",
        autoscaling=True,
        scaling_config={
            "min_replicas": 1,
            "max_replicas": 5,
            "policy": "default",
        },
    )


class TestAddonsManifestConstructor:
    def test_empty(self, bk_module, blank_resource):
        AddonsManifestConstructor().apply_to(blank_resource, bk_module)

        assert len(blank_resource.spec.addons) == 0

    def test_with_addons(self, bk_module, blank_resource, local_service):
        mixed_service_mgr.bind_service(local_service, bk_module)
        AddonsManifestConstructor().apply_to(blank_resource, bk_module)

        assert len(blank_resource.spec.addons) == 1
        assert blank_resource.spec.addons[0] == crd.BkAppAddon(name="mysql")

    def test_with_shared_addons(self, bk_module, bk_module_2, blank_resource, local_service):
        # Let bk_module share a service with bk_module_2
        mixed_service_mgr.bind_service(local_service, bk_module_2)
        ServiceSharingManager(bk_module).create(local_service, bk_module_2)

        AddonsManifestConstructor().apply_to(blank_resource, bk_module)

        assert len(blank_resource.spec.addons) == 1
        assert blank_resource.spec.addons[0] == crd.BkAppAddon(name="mysql", sharedFromModule=bk_module_2.name)


class TestEnvVarsManifestConstructor:
    def test_integrated(self, bk_module, bk_stag_env, blank_resource):
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="FOO_STAG", value="1")
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="BAR", value="1")
        ConfigVar.objects.create(
            module=bk_module,
            environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
            key="BAR",
            value="2",
            is_global=True,
        )

        EnvVarsManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.configuration.env == [crd.EnvVar(name="BAR", value="2")]
        assert blank_resource.spec.envOverlay.envVariables == [
            crd.EnvVarOverlay(envName="stag", name="BAR", value="1"),
            crd.EnvVarOverlay(envName="stag", name="FOO_STAG", value="1"),
        ]

    def test_preset(self, bk_module, bk_stag_env, blank_resource):
        G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.GLOBAL, key="GLOBAL", value="1")
        G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.STAG, key="STAG", value="1")
        G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.PROD, key="PROD", value="1")

        EnvVarsManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.configuration.env == [crd.EnvVar(name="GLOBAL", value="1")]
        assert blank_resource.spec.envOverlay.envVariables == [
            crd.EnvVarOverlay(envName="prod", name="PROD", value="1"),
            crd.EnvVarOverlay(envName="stag", name="STAG", value="1"),
        ]

    def test_override_preset(self, bk_module, bk_stag_env, blank_resource):
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="STAG", value="2")
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="STAG_XX", value="2")
        G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.GLOBAL, key="GLOBAL", value="1")
        G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.STAG, key="STAG", value="1")
        G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.PROD, key="PROD", value="1")
        # case: 是否覆盖与顺序无关.
        ConfigVar.objects.create(
            module=bk_module,
            environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
            key="GLOBAL",
            value="2",
            is_global=True,
        )

        EnvVarsManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.configuration.env == [crd.EnvVar(name="GLOBAL", value="2")]
        assert blank_resource.spec.envOverlay.envVariables == [
            crd.EnvVarOverlay(envName="prod", name="PROD", value="1"),
            crd.EnvVarOverlay(envName="stag", name="STAG", value="2"),
            crd.EnvVarOverlay(envName="stag", name="STAG_XX", value="2"),
        ]


class TestBuiltinAnnotsManifestConstructor:
    def test_normal(self, bk_module, blank_resource):
        app = bk_module.application
        BuiltinAnnotsManifestConstructor().apply_to(blank_resource, bk_module)

        annots = blank_resource.metadata.annotations
        assert (
            annots["bkapp.paas.bk.tencent.com/image-credentials"]
            == f"{generate_bkapp_name(bk_module)}--dockerconfigjson"
        )
        assert annots["bkapp.paas.bk.tencent.com/module-name"] == bk_module.name
        assert annots["bkapp.paas.bk.tencent.com/name"] == app.name
        assert annots["bkapp.paas.bk.tencent.com/region"] == app.region


class TestProcessesManifestConstructor:
    @pytest.fixture()
    def process_web_autoscaling(self, process_web) -> ModuleProcessSpec:
        """ProcessSpec for web, with autoscaling enabled"""
        process_web.autoscaling = True
        process_web.scaling_config = {"min_replicas": 1, "max_replicas": 2, "policy": "default"}
        process_web.save()
        return process_web

    @pytest.fixture()
    def process_web_with_proc_services(self, process_web) -> ModuleProcessSpec:
        """ProcessSpec for web, with services"""
        process_web.services = [
            ProcService(
                name="web",
                port=8000,
                target_port=8000,
                exposed_type={"name": "bk/http"},
            ),
            ProcService(name="metric", port=8001, target_port=8001),
        ]
        process_web.save()
        return process_web

    @pytest.mark.parametrize(
        ("plan_name", "expected"),
        [
            ("", ResQuotaPlan.P_DEFAULT),
            (settings.DEFAULT_PROC_SPEC_PLAN, ResQuotaPlan.P_DEFAULT),
            (settings.PREMIUM_PROC_SPEC_PLAN, ResQuotaPlan.P_4C2G),
            # Memory 稀缺性比 CPU 要高, 转换时只关注 Memory
            (settings.ULTIMATE_PROC_SPEC_PLAN, ResQuotaPlan.P_4C4G),
            (ResQuotaPlan.P_4C1G, ResQuotaPlan.P_4C1G),
        ],
    )
    def test_get_quota_plan(self, plan_name, expected):
        initialize_default_proc_spec_plans()
        assert ProcessesManifestConstructor().get_quota_plan(plan_name) == expected

    @pytest.mark.parametrize(
        ("build_method", "is_cnb_runtime", "expected"),
        [
            (RuntimeType.BUILDPACK, False, (DEFAULT_SLUG_RUNNER_ENTRYPOINT, ["start", "web"])),
            (RuntimeType.BUILDPACK, True, (DEFAULT_SLUG_RUNNER_ENTRYPOINT, ["start", "web"])),
            (RuntimeType.DOCKERFILE, False, (["python"], ["-m", "http.server"])),
        ],
    )
    def test_get_command_and_args(self, bk_module, process_web, build_method, is_cnb_runtime, expected):
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        cfg.build_method = build_method
        cfg.save()
        with mock.patch("paasng.platform.bkapp_model.manifest.ModuleRuntimeManager.is_cnb_runtime", is_cnb_runtime):
            assert ProcessesManifestConstructor().get_command_and_args(bk_module, process_web) == expected

    def test_get_command_and_args_invalid_var_expr(self, bk_module):
        """Test get_command_and_args() when there is an invalid env var expression."""
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        cfg.build_method = RuntimeType.DOCKERFILE
        cfg.save(update_fields=["build_method"])

        proc = G(ModuleProcessSpec, module=bk_module, name="web", proc_command="start -b ${PORT:-5000}")

        assert ProcessesManifestConstructor().get_command_and_args(bk_module, proc) == (
            ["start"],
            ["-b", "${PORT}"],
        ), "The ${PORT:-5000} should be replaced."

    def test_integrated(self, bk_module, blank_resource, process_web, process_web_overlay):
        initialize_default_proc_spec_plans()
        ProcessesManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.dict(include={"processes", "envOverlay"}) == {
            "processes": [
                {
                    "name": "web",
                    "replicas": 1,
                    "command": ["bash", "/runner/init"],
                    "args": ["start", "web"],
                    "targetPort": 8000,
                    "resQuotaPlan": "default",
                    "autoscaling": None,
                    "probes": None,
                    "services": None,
                }
            ],
            "envOverlay": {
                "replicas": [{"envName": "stag", "process": "web", "count": 10}],
                "autoscaling": [
                    {
                        "envName": "stag",
                        "process": "web",
                        "minReplicas": 1,
                        "maxReplicas": 5,
                        "policy": "default",
                    }
                ],
                "envVariables": None,
                "mounts": None,
                "resQuotas": [
                    {
                        "envName": "stag",
                        "process": "web",
                        # The plan name should have been transformed.
                        "plan": "default",
                    }
                ],
            },
        }

    def test_integrated_autoscaling(self, bk_module, blank_resource, process_web_autoscaling):
        initialize_default_proc_spec_plans()
        ProcessesManifestConstructor().apply_to(blank_resource, bk_module)
        data = blank_resource.spec.dict(include={"processes"})["processes"][0]
        assert data["autoscaling"] == {
            "minReplicas": 1,
            "maxReplicas": 2,
            "policy": "default",
        }

    def test_integrated_proc_services(self, bk_module, blank_resource, process_web_with_proc_services):
        ProcessesManifestConstructor().apply_to(blank_resource, bk_module)
        data = blank_resource.spec.dict(exclude_none=True, include={"processes"})["processes"][0]
        assert data["services"] == [
            {"name": "web", "port": 8000, "protocol": "TCP", "targetPort": 8000, "exposedType": {"name": "bk/http"}},
            {"name": "metric", "port": 8001, "protocol": "TCP", "targetPort": 8001},
        ]


class TestMountsManifestConstructor:
    def test_normal(self, bk_module, blank_resource):
        create_mount = functools.partial(
            G,
            model=Mount,
            module_id=bk_module.id,
            name="nginx",
            source_type=VolumeSourceType.ConfigMap,
            source_config=crd.VolumeSource(configMap=crd.ConfigMapSource(name="nginx-configmap")),
        )
        # Create 2 mount objects
        create_mount(mount_path="/etc/conf", environment_name=MountEnvName.GLOBAL.value)
        create_mount(mount_path="/etc/conf_stag", environment_name=MountEnvName.STAG.value)

        MountsManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.mounts == [
            crd.Mount(
                mountPath="/etc/conf",
                name="nginx",
                source=crd.VolumeSource(configMap=crd.ConfigMapSource(name="nginx-configmap")),
            )
        ]
        assert blank_resource.spec.envOverlay.mounts == [
            crd.MountOverlay(
                envName="stag",
                mountPath="/etc/conf_stag",
                name="nginx",
                source=crd.VolumeSource(configMap=crd.ConfigMapSource(name="nginx-configmap")),
            )
        ]


class TestHooksManifestConstructor:
    def test_normal(self, bk_module, blank_resource):
        bk_module.deploy_hooks.enable_hook(type_=DeployHookType.PRE_RELEASE_HOOK, command=["python"], args=["hook.py"])
        HooksManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.hooks == crd.BkAppHooks(
            preRelease={
                "command": ["python"],
                "args": ["hook.py"],
            }
        )

    def test_proc_command(self, bk_module, blank_resource):
        bk_module.deploy_hooks.enable_hook(type_=DeployHookType.PRE_RELEASE_HOOK, proc_command="python hook.py")
        HooksManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.hooks == crd.BkAppHooks(
            preRelease={
                "command": ["python"],
                "args": ["hook.py"],
            }
        )

    def test_not_found(self, bk_module, blank_resource):
        HooksManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.hooks == crd.BkAppHooks()

    def test_empty_command(self, bk_module, blank_resource):
        bk_module.deploy_hooks.enable_hook(type_=DeployHookType.PRE_RELEASE_HOOK, args=["hook.py"])
        HooksManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.hooks == crd.BkAppHooks(preRelease={"args": ["hook.py"]})


class TestSvcDiscoveryManifestConstructor:
    def test_normal(self, bk_app, bk_module, blank_resource):
        G(
            SvcDiscConfig,
            application=bk_app,
            bk_saas=[
                {"bkAppCode": "foo"},
                {"bkAppCode": "bar", "moduleName": "default"},
                {"bkAppCode": "bar", "moduleName": "opps"},
            ],
        )

        SvcDiscoveryManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.svcDiscovery == crd.SvcDiscConfig(
            bkSaaS=[
                crd.SvcDiscEntryBkSaaS(bkAppCode="foo"),
                crd.SvcDiscEntryBkSaaS(bkAppCode="bar", moduleName="default"),
                crd.SvcDiscEntryBkSaaS(bkAppCode="bar", moduleName="opps"),
            ],
        )


class TestDomainResolutionManifestConstructor:
    def test_normal(self, bk_app, bk_module, blank_resource):
        # Create domain_resolution object
        G(
            DomainResolution,
            application=bk_app,
            nameservers=["192.168.1.3", "192.168.1.4"],
            host_aliases=[
                {
                    "ip": "1.1.1.1",
                    "hostnames": [
                        "bk_app_code_test",
                        "bk_app_code_test_z",
                    ],
                }
            ],
        )

        DomainResolutionManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.domainResolution == crd.DomainResolution(
            nameservers=["192.168.1.3", "192.168.1.4"],
            hostAliases=[
                crd.HostAlias(
                    ip="1.1.1.1",
                    hostnames=[
                        "bk_app_code_test",
                        "bk_app_code_test_z",
                    ],
                )
            ],
        )


def test_get_manifest(bk_module):
    manifest = get_manifest(bk_module)
    assert len(manifest) > 0
    assert manifest[0]["kind"] == "BkApp"


@pytest.mark.usefixtures("_with_wl_apps")
def test_apply_env_annots(blank_resource, bk_stag_env):
    apply_env_annots(blank_resource, bk_stag_env)

    annots = blank_resource.metadata.annotations
    assert annots["bkapp.paas.bk.tencent.com/environment"] == "stag"
    assert annots["bkapp.paas.bk.tencent.com/wl-app-name"] == bk_stag_env.wl_app.name
    assert "bkapp.paas.bk.tencent.com/bkpaas-deploy-id" not in annots


@pytest.mark.usefixtures("_with_wl_apps")
def test_apply_env_annots_with_deploy_id(blank_resource, bk_stag_env):
    apply_env_annots(blank_resource, bk_stag_env, deploy_id="foo-id")
    assert blank_resource.metadata.annotations["bkapp.paas.bk.tencent.com/bkpaas-deploy-id"] == "foo-id"


@pytest.mark.usefixtures("_with_wl_apps")
def test_apply_builtin_env_vars(blank_resource, bk_stag_env, bk_deployment):
    G(
        DeploymentDescription,
        deployment=bk_deployment,
        env_variables=[
            {"key": "FOO", "value": "1", "environment_name": "_global_"},
            {"key": "BAR", "value": "2", "environment_name": "stag"},
        ],
        runtime={
            "svc_discovery": {
                "bk_saas": [
                    {"bk_app_code": "foo-app"},
                    {"bk_app_code": "bar-app", "module_name": "api"},
                ]
            },
        },
    )

    apply_builtin_env_vars(blank_resource, bk_stag_env)
    var_names = {item.name for item in blank_resource.spec.configuration.env}
    for name in (
        "BKPAAS_APP_ID",
        "BKPAAS_APP_SECRET",
        "BK_LOGIN_URL",
        "BK_DOCS_URL_PREFIX",
        "BKPAAS_DEFAULT_PREALLOCATED_URLS",
    ):
        assert name in var_names
    # 验证描述文件中声明的环境变量不会通过 apply_builtin_env_vars 注入(而是在更上层的组装 manifest 时处理)
    assert "FOO" not in var_names
    assert "BAR" not in var_names
    # 应用描述文件中申明了服务发现的话，不会写入相关的环境变量(云原生应用的服务发现通过 configmap 注入环境变量)
    assert "BKPAAS_SERVICE_ADDRESSES_BKSAAS" not in var_names


@pytest.mark.usefixtures("_with_wl_apps")
def test_builtin_env_has_high_priority(blank_resource, bk_stag_env):
    custom_login_url = generate_random_string()

    blank_resource.spec.envOverlay = crd.EnvOverlay()
    blank_resource.spec.envOverlay.envVariables = [
        crd.EnvVarOverlay(name="BK_LOGIN_URL", value=custom_login_url, envName="stag")
    ]

    apply_builtin_env_vars(blank_resource, bk_stag_env)
    vars = {item.name: item.value for item in blank_resource.spec.configuration.env}
    vars_overlay = {(v.name, v.envName): v.value for v in blank_resource.spec.envOverlay.envVariables}

    assert vars_overlay[("BK_LOGIN_URL", "stag")] != custom_login_url
    assert vars["BK_LOGIN_URL"] == vars_overlay[("BK_LOGIN_URL", "stag")]
