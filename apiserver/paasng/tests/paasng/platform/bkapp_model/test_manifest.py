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
from typing import Dict
from unittest import mock

import pytest
from attr import define
from django.conf import settings
from django.test import override_settings
from django_dynamic_fixture import G

from paas_wl.bk_app.applications.entities import BuildArtifactMetadata
from paas_wl.bk_app.applications.models.build import Build as WlBuild
from paas_wl.bk_app.cnative.specs.constants import (
    BKAPP_TENANT_ID_ANNO_KEY,
    TENANT_GUARD_ANNO_KEY,
    ApiVersion,
    MountEnvName,
    VolumeSourceType,
)
from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.cnative.specs.crd.metadata import ObjectMetadata
from paas_wl.bk_app.cnative.specs.models import Mount
from paas_wl.bk_app.processes.models import initialize_default_proc_spec_plans
from paas_wl.core.resource import generate_bkapp_name
from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.bkapp_model.constants import ResQuotaPlan
from paasng.platform.bkapp_model.entities import Component, ProcService
from paasng.platform.bkapp_model.manifest import (
    AddonsManifestConstructor,
    BuiltinAnnotsManifestConstructor,
    DomainResolutionManifestConstructor,
    EnvVarsManifestConstructor,
    HooksManifestConstructor,
    MountsManifestConstructor,
    ObservabilityManifestConstructor,
    ProcessesManifestConstructor,
    SvcDiscoveryManifestConstructor,
    _update_cmd_args_from_wl_build,
    apply_builtin_env_vars,
    apply_env_annots,
    get_manifest,
)
from paasng.platform.bkapp_model.models import (
    DomainResolution,
    ModuleProcessSpec,
    ObservabilityConfig,
    ProcessSpecEnvOverlay,
    SvcDiscConfig,
)
from paasng.platform.declarative.deployment.controller import DeploymentDescription
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.constants import DeployHookType
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def blank_resource() -> crd.BkAppResource:
    """A blank resource object."""
    return crd.BkAppResource(
        apiVersion=ApiVersion.V1ALPHA2, metadata=ObjectMetadata(name="a-blank-resource"), spec=crd.BkAppSpec()
    )


@pytest.fixture()
def blank_resource_with_processes() -> crd.BkAppResource:
    """A resource object have processes spec."""
    return crd.BkAppResource(
        apiVersion=ApiVersion.V1ALPHA2,
        metadata=ObjectMetadata(name="a-blank-resource"),
        spec=crd.BkAppSpec(
            processes=[
                crd.BkAppProcess(name="worker"),
                crd.BkAppProcess(name="web"),
            ]
        ),
    )


@pytest.fixture()
def local_service(bk_app):
    """A local service object."""
    service = G(Service, name="mysql", category=G(ServiceCategory), logo_b64="dummy")
    _ = G(Plan, name=generate_random_string(), service=service)
    svc_obj = mixed_service_mgr.get(service.uuid)
    SvcBindingPolicyManager(svc_obj, DEFAULT_TENANT_ID).set_uniform(plans=[svc_obj.get_plans()[0].uuid])
    return svc_obj


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
            ProcService(name="metric", port=8001, target_port="${PORT}"),
        ]
        process_web.save()
        return process_web

    @pytest.fixture()
    def process_web_with_proc_components(self, process_web) -> ModuleProcessSpec:
        """ProcessSpec for web, with components"""
        process_web.components = [
            Component(
                name="env_overlay",
                version="v1",
                properties={"env": [{"name": "proc_name", "value": "FOO"}, {"name": "key", "value": "1"}]},
            ),
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

    def test_get_command_and_args(self, bk_module, process_web):
        assert ProcessesManifestConstructor().get_command_and_args(process_web) == (
            ["python"],
            ["-m", "http.server"],
        )

    def test_get_command_and_args_invalid_var_expr(self, bk_module):
        """Test get_command_and_args() when there is an invalid env var expression."""
        proc = G(ModuleProcessSpec, module=bk_module, name="web", proc_command="start -b ${PORT:-5000}")

        assert ProcessesManifestConstructor().get_command_and_args(proc) == (
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
                    "command": ["python"],
                    "args": ["-m", "http.server"],
                    "targetPort": 8000,
                    "resQuotaPlan": "default",
                    "autoscaling": None,
                    "probes": None,
                    "services": None,
                    "components": None,
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
            {"name": "metric", "port": 8001, "protocol": "TCP", "targetPort": settings.CONTAINER_PORT},
        ]

    def test_integrated_proc_components(self, bk_module, blank_resource, process_web_with_proc_components):
        ProcessesManifestConstructor().apply_to(blank_resource, bk_module)
        data = blank_resource.spec.dict(exclude_none=True, include={"processes"})["processes"][0]
        assert data["components"] == [
            {
                "properties": '{"env": [{"name": "proc_name", "value": "FOO"}, {"name": ' '"key", "value": "1"}]}',
                "name": "env_overlay",
                "version": "v1",
            },
        ]


class TestMountsManifestConstructor:
    def test_normal(self, bk_module, blank_resource):
        create_mount = functools.partial(
            G,
            model=Mount,
            module_id=bk_module.id,
            name="nginx",
            source_type=VolumeSourceType.ConfigMap,
            sub_paths=["configmap_z"],
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
                subPaths=["configmap_z"],
            )
        ]
        assert blank_resource.spec.envOverlay.mounts == [
            crd.MountOverlay(
                envName="stag",
                mountPath="/etc/conf_stag",
                name="nginx",
                source=crd.VolumeSource(configMap=crd.ConfigMapSource(name="nginx-configmap")),
                subPaths=["configmap_z"],
            )
        ]

    def test_tls_credentials(self, bk_module, blank_resource):
        @define
        class FakeSvcInstance:
            config: Dict[str, str]

        @define
        class FakeSvcRelation:
            instance: FakeSvcInstance

            def get_instance(self):
                return self.instance

        with mock.patch(
            "paasng.platform.bkapp_model.manifest.list_provisioned_tls_enabled_rels",
            new=lambda env: (
                [
                    FakeSvcRelation(instance=FakeSvcInstance(config={"provider_name": "redis"})),
                    FakeSvcRelation(instance=FakeSvcInstance(config={"provider_name": "mysql"})),
                ]
                if env.environment == "stag"
                else []
            ),
        ):
            MountsManifestConstructor().apply_to(blank_resource, bk_module)
            assert blank_resource.spec.envOverlay.mounts == [
                crd.MountOverlay(
                    envName="stag",
                    mountPath="/opt/blueking/bkapp-addons-certs/redis",
                    name="bkapp-addons-certs-redis",
                    source=crd.VolumeSource(secret=crd.SecretSource(name="bkapp-addons-certs-redis")),
                ),
                crd.MountOverlay(
                    envName="stag",
                    mountPath="/opt/blueking/bkapp-addons-certs/mysql",
                    name="bkapp-addons-certs-mysql",
                    source=crd.VolumeSource(secret=crd.SecretSource(name="bkapp-addons-certs-mysql")),
                ),
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


class TestObservabilityManifestConstructor:
    def test_normal(self, bk_app, bk_module, blank_resource):
        G(
            ObservabilityConfig,
            module=bk_module,
            monitoring={
                "metrics": [{"process": "web", "service_name": "metric", "path": "/metrics", "params": {"foo": "bar"}}]
            },
        )
        ObservabilityManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.observability == crd.Observability(
            monitoring=crd.Monitoring(
                metrics=[crd.Metric(process="web", serviceName="metric", path="/metrics", params={"foo": "bar"})]
            )
        )

    def test_with_no_observability(self, bk_app, bk_module, blank_resource):
        ObservabilityManifestConstructor().apply_to(blank_resource, bk_module)
        assert blank_resource.spec.observability is None


def test_get_manifest(bk_module):
    manifest = get_manifest(bk_module)
    assert len(manifest) > 0
    assert manifest[0]["kind"] == "BkApp"
    assert manifest[0]["metadata"]["annotations"][BKAPP_TENANT_ID_ANNO_KEY] == bk_module.application.app_tenant_id


@pytest.mark.parametrize(("enable_multi_tenant_mode", "expected"), [(True, "true"), (False, "false")])
def test_get_tenant_guard(bk_module, enable_multi_tenant_mode, expected):
    with override_settings(ENABLE_MULTI_TENANT_MODE=enable_multi_tenant_mode):
        manifest = get_manifest(bk_module)
        assert manifest[0]["metadata"]["annotations"][TENANT_GUARD_ANNO_KEY] == expected


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


class Test__update_cmd_args_from_wl_build:
    @pytest.fixture()
    def bk_app_resource(self):
        return crd.BkAppResource(
            apiVersion=ApiVersion.V1ALPHA2,
            metadata=ObjectMetadata(name="a-test-resource"),
            spec=crd.BkAppSpec(
                hooks=crd.BkAppHooks(
                    preRelease=crd.Hook(
                        command=["python"],
                        args=["hook.py"],
                    )
                ),
                processes=[
                    crd.BkAppProcess(name="worker", command=["celery"], args=["worker", "-l", "info"]),
                    crd.BkAppProcess(name="web", command=["python"], args=["manage.py", "runserver"]),
                ],
            ),
        )

    @pytest.mark.parametrize(
        ("artifact_metadata", "expected_hook", "expected_processes"),
        [
            # 非 cnb 构建(不设置)
            (
                BuildArtifactMetadata(),
                crd.Hook(
                    command=["bash", "/runner/init", "python"],
                    args=["hook.py"],
                ),
                [
                    crd.BkAppProcess(name="worker", command=["bash", "/runner/init"], args=["start", "worker"]),
                    crd.BkAppProcess(name="web", command=["bash", "/runner/init"], args=["start", "web"]),
                ],
            ),
            # 非 cnb 构建(显式设置)
            (
                BuildArtifactMetadata(use_cnb=False),
                crd.Hook(
                    command=["bash", "/runner/init", "python"],
                    args=["hook.py"],
                ),
                [
                    crd.BkAppProcess(name="worker", command=["bash", "/runner/init"], args=["start", "worker"]),
                    crd.BkAppProcess(name="web", command=["bash", "/runner/init"], args=["start", "web"]),
                ],
            ),
            # cnb 构建
            (
                BuildArtifactMetadata(use_cnb=True),
                crd.Hook(
                    command=["launcher", "python"],
                    args=["hook.py"],
                ),
                [
                    crd.BkAppProcess(name="worker", command=["worker"], args=[]),
                    crd.BkAppProcess(name="web", command=["web"], args=[]),
                ],
            ),
            # 指定了 proc_entrypoints 的 cnb 构建
            (
                BuildArtifactMetadata(
                    use_cnb=True, proc_entrypoints={"web": ["frontend-web"], "worker": ["backend-worker"]}
                ),
                crd.Hook(
                    command=["launcher", "python"],
                    args=["hook.py"],
                ),
                [
                    crd.BkAppProcess(name="worker", command=["backend-worker"], args=[]),
                    crd.BkAppProcess(name="web", command=["frontend-web"], args=[]),
                ],
            ),
        ],
    )
    def test_update(self, bk_app_resource, artifact_metadata, expected_hook, expected_processes):
        wl_build = WlBuild.objects.create(artifact_metadata=artifact_metadata)

        _update_cmd_args_from_wl_build(bk_app_resource, wl_build)

        assert bk_app_resource.spec.hooks.preRelease == expected_hook
        assert bk_app_resource.spec.processes == expected_processes
