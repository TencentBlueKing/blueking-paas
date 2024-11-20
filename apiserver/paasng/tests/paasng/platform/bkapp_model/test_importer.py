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

import copy
import functools

import pytest

from paas_wl.bk_app.cnative.specs.models import Mount
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.constants import ResQuotaPlan, ScalingPolicy
from paasng.platform.bkapp_model.entities import AutoscalingConfig, Metric, SvcDiscEntryBkSaaS
from paasng.platform.bkapp_model.exceptions import ManifestImportError
from paasng.platform.bkapp_model.importer import import_manifest
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ObservabilityConfig, SvcDiscConfig
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.utils.camel_converter import dict_to_camel

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

import_manifest_app_desc = functools.partial(import_manifest, manager=fieldmgr.FieldMgrName.APP_DESC)


@pytest.fixture()
def base_manifest(bk_app):
    """A very basic manifest that can pass the validation."""
    return {
        "kind": "BkApp",
        "apiVersion": "paas.bk.tencent.com/v1alpha2",
        "metadata": {"name": bk_app.code},
        "spec": {
            "build": {"image": "nginx:latest"},
            "processes": [{"name": "web", "replicas": 1, "resQuotaPlan": "default"}],
        },
    }


@pytest.fixture()
def manifest_no_replicas(base_manifest):
    """A very basic manifest that can pass the validation, contains no `replicas` field."""
    data = copy.deepcopy(base_manifest)
    del data["spec"]["processes"][0]["replicas"]
    return data


@pytest.fixture()
def manifest_replicas_3(manifest_no_replicas):
    data = copy.deepcopy(manifest_no_replicas)
    data["spec"]["processes"][0]["replicas"] = 3
    return data


class TestProcReplicas:
    def test_initialization(self, bk_module, manifest_no_replicas):
        import_manifest_app_desc(bk_module, manifest_no_replicas)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.target_replicas == 1

    def test_reset_by_notset(self, bk_module, manifest_no_replicas, manifest_replicas_3):
        import_manifest_app_desc(bk_module, manifest_replicas_3)

        import_manifest_app_desc(bk_module, manifest_no_replicas)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.target_replicas == 1, "The replicas should has been reset"
        assert fieldmgr.FieldManager(bk_module, fieldmgr.f_proc_replicas("web")).get() is None

    def test_ignore_not_managed_when_notset(self, bk_module, manifest_no_replicas, manifest_replicas_3):
        import_manifest(bk_module, manifest_replicas_3, manager=fieldmgr.FieldMgrName.WEB_FORM)

        import_manifest_app_desc(bk_module, manifest_no_replicas)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.target_replicas == 3, "The replicas should remain as it is"

    def test_set_to_zero(self, bk_module, manifest_no_replicas):
        import_manifest_app_desc(bk_module, manifest_no_replicas)
        manifest_replicas_0 = copy.deepcopy(manifest_no_replicas)
        manifest_replicas_0["spec"]["processes"][0]["replicas"] = 0

        import_manifest_app_desc(bk_module, manifest_replicas_0)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.target_replicas == 0, "The replicas should be set to 0"


class TestProcAutoscaling:
    @pytest.fixture()
    def manifest_autoscaling(self, base_manifest):
        """A manifest with autoscaling enabled."""
        manifest = copy.deepcopy(base_manifest)
        manifest["spec"]["processes"][0]["autoscaling"] = {
            "minReplicas": 1,
            "maxReplicas": 2,
            "policy": ScalingPolicy.DEFAULT,
        }
        return manifest

    def test_enable(self, bk_module, base_manifest, manifest_autoscaling):
        import_manifest_app_desc(bk_module, base_manifest)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.autoscaling is False
        assert proc_spec.scaling_config is None

        import_manifest_app_desc(bk_module, manifest_autoscaling)
        proc_spec.refresh_from_db()
        assert proc_spec.autoscaling is True
        assert proc_spec.scaling_config.max_replicas == 2
        assert (
            fieldmgr.FieldManager(bk_module, fieldmgr.f_proc_autoscaling("web")).get()
            == fieldmgr.FieldMgrName.APP_DESC
        )

    def test_disable_by_notset(self, bk_module, base_manifest, manifest_autoscaling):
        import_manifest_app_desc(bk_module, manifest_autoscaling)

        # When the field is not set, the autoscaling should be disabled.
        import_manifest_app_desc(bk_module, base_manifest)
        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")

        assert proc_spec.autoscaling is False
        assert proc_spec.scaling_config is None
        assert fieldmgr.FieldManager(bk_module, fieldmgr.f_proc_autoscaling("web")).get() is None

    def test_ignore_not_managed_when_notset(self, bk_module, base_manifest, manifest_autoscaling):
        import_manifest(bk_module, manifest_autoscaling, manager=fieldmgr.FieldMgrName.WEB_FORM)

        # When the field is not set and it's managed by another manager, the autoscaling
        # should remain as it is.
        import_manifest_app_desc(bk_module, base_manifest)
        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.autoscaling is True
        assert proc_spec.scaling_config.max_replicas == 2


def test_import_with_enum_type(bk_module, base_manifest):
    """test import from bkapp serialize from pydantic"""
    base_manifest["spec"]["processes"] = [
        {
            "name": "web",
            "replicas": 1,
            "resQuotaPlan": ResQuotaPlan.P_DEFAULT,
            "autoscaling": {
                "minReplicas": 1,
                "maxReplicas": 2,
                "policy": ScalingPolicy.DEFAULT,
            },
        }
    ]
    import_manifest_app_desc(bk_module, base_manifest)
    proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
    assert proc_spec.plan_name == ResQuotaPlan.P_DEFAULT.value
    assert proc_spec.scaling_config == AutoscalingConfig(min_replicas=1, max_replicas=2, policy=ScalingPolicy.DEFAULT)


class TestEnvVars:
    def test_invalid_name_input(self, bk_module, base_manifest):
        # Names in lower case are forbidden.
        base_manifest["spec"]["configuration"] = {"env": [{"name": "foo", "value": "foo"}]}
        with pytest.raises(ManifestImportError) as e:
            import_manifest_app_desc(bk_module, base_manifest)

        assert "configuration.env.0.name" in str(e)

    def test_normal(self, bk_module, base_manifest):
        base_manifest["spec"]["configuration"] = {"env": [{"name": "KEY1", "value": "foo"}]}
        base_manifest["spec"]["envOverlay"] = {"envVariables": [{"envName": "stag", "name": "KEY2", "value": "foo"}]}

        import_manifest_app_desc(bk_module, base_manifest)
        assert PresetEnvVariable.objects.count() == 2


class TestAddons:
    def test_invalid_value(self, bk_module, base_manifest):
        base_manifest["spec"]["addons"] = [{"foo": "bar"}]
        with pytest.raises(ManifestImportError) as e:
            import_manifest_app_desc(bk_module, base_manifest)

        assert "addons.0.name" in str(e)

    def test_invalid_spec(self, bk_module, base_manifest):
        base_manifest["spec"]["addons"] = [{"name": "mysql", "specs": [{"foo": "bar"}]}]
        with pytest.raises(ManifestImportError) as e:
            import_manifest_app_desc(bk_module, base_manifest)

        assert "addons.0.specs" in str(e)

    def test_normal(self, bk_module, base_manifest):
        base_manifest["spec"]["addons"] = [{"name": "mysql"}]
        import_manifest_app_desc(bk_module, base_manifest)
        # TODO: Add assertion to verify the addons have been imported successfully


class TestMounts:
    def test_invalid_mount_path_input(self, bk_module, base_manifest):
        base_manifest["spec"]["mounts"] = [
            # mountPath must starts with "/"
            {"name": "nginx-conf", "mountPath": "___/etc/nginx", "source": {"configMap": {"name": "nginx-conf-cm"}}}
        ]
        with pytest.raises(ManifestImportError) as e:
            import_manifest_app_desc(bk_module, base_manifest)

        assert "mounts.0.mountPath" in str(e)

    def test_normal(self, bk_module, base_manifest):
        base_manifest["spec"]["mounts"] = [
            {"name": "nginx-conf", "mountPath": "/etc/nginx", "source": {"configMap": {"name": "nginx-conf-cm"}}}
        ]
        base_manifest["spec"]["envOverlay"] = {
            "mounts": [
                {
                    "envName": "stag",
                    "name": "nginx-conf-stag",
                    "mountPath": "/etc/nginx_stag",
                    "source": {"configMap": {"name": "nginx-conf-cm"}},
                }
            ]
        }

        import_manifest_app_desc(bk_module, base_manifest)
        assert Mount.objects.count() == 2


class TestReplicasOverlay:
    @pytest.fixture()
    def base_manifest_with_overlay(self, base_manifest):
        d = copy.deepcopy(base_manifest)
        d["spec"]["envOverlay"] = {
            "replicas": [
                {
                    "envName": "stag",
                    "process": "web",
                    "count": "3",
                }
            ]
        }
        return d

    def test_invalid_replicas_input(self, bk_module, base_manifest):
        base_manifest["spec"]["envOverlay"] = {
            "replicas": [
                {
                    "envName": "stag",
                    "process": "web",
                    "count": "not_a_number",
                }
            ]
        }
        with pytest.raises(ManifestImportError) as e:
            import_manifest_app_desc(bk_module, base_manifest)

        assert "envOverlay.replicas.0.count" in str(e)

    def test_str(self, bk_module, base_manifest_with_overlay):
        import_manifest_app_desc(bk_module, base_manifest_with_overlay)
        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.get_target_replicas("stag") == 3

    def test_reset_by_not_providing_value(self, bk_module, base_manifest, base_manifest_with_overlay):
        import_manifest_app_desc(bk_module, base_manifest_with_overlay)
        import_manifest_app_desc(bk_module, base_manifest)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.get_target_replicas("stag") == 1, "The overlay data should be reset"

    def test_not_reset_when_manager_different(self, bk_module, base_manifest, base_manifest_with_overlay):
        import_manifest_app_desc(bk_module, base_manifest_with_overlay)
        import_manifest(bk_module, base_manifest, manager=fieldmgr.FieldMgrName.WEB_FORM)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.get_target_replicas("stag") == 3, "The overlay data should remain as it is"


class TestAutoscaling:
    def test_normal(self, bk_module, base_manifest):
        base_manifest["spec"]["envOverlay"] = {
            "autoscaling": [
                {
                    "envName": "stag",
                    "process": "web",
                    "minReplicas": 1,
                    "maxReplicas": 1,
                    "policy": "default",
                }
            ]
        }
        import_manifest_app_desc(bk_module, base_manifest)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.get_autoscaling("stag")
        assert proc_spec.get_scaling_config("stag") == AutoscalingConfig(
            min_replicas=1, max_replicas=1, policy=ScalingPolicy.DEFAULT
        )

    def test_missing_policy(self, bk_module, base_manifest):
        base_manifest["spec"]["envOverlay"] = {
            "autoscaling": [
                {
                    "envName": "stag",
                    "process": "web",
                    "minReplicas": 1,
                    "maxReplicas": 1,
                }
            ]
        }
        import_manifest_app_desc(bk_module, base_manifest)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.get_autoscaling("stag")
        assert proc_spec.get_scaling_config("stag") == AutoscalingConfig(
            min_replicas=1, max_replicas=1, policy=ScalingPolicy.DEFAULT
        )


class TestSvcDiscConfig:
    def test_normal(self, bk_app, bk_module, base_manifest):
        base_manifest["spec"]["svcDiscovery"] = {
            "bkSaaS": [
                {"bkAppCode": "foo"},
                {"bkAppCode": "bar", "moduleName": "default"},
                {"bkAppCode": "bar", "moduleName": "opps"},
            ]
        }

        import_manifest_app_desc(bk_module, base_manifest)
        cfg = SvcDiscConfig.objects.get(application=bk_app)

        assert cfg.bk_saas == [
            SvcDiscEntryBkSaaS(bk_app_code="foo"),
            SvcDiscEntryBkSaaS(bk_app_code="bar", module_name="default"),
            SvcDiscEntryBkSaaS(bk_app_code="bar", module_name="opps"),
        ]


class TestObservability:
    @pytest.fixture()
    def manifest(self, base_manifest):
        base_manifest["spec"]["processes"][0]["services"] = [{"name": "metric", "targetPort": "8080"}]
        return base_manifest

    def test_normal(self, bk_module, manifest):
        metric = {"process": "web", "service_name": "metric", "path": "/metrics", "params": {"foo": "bar"}}
        manifest["spec"]["observability"] = {
            "monitoring": {"metrics": [dict_to_camel(metric)]},
        }
        import_manifest_app_desc(bk_module, manifest)

        observability = ObservabilityConfig.objects.get(module=bk_module)
        assert observability.monitoring.metrics == [Metric(**metric)]

    def test_with_no_monitoring(self, bk_module, base_manifest):
        import_manifest_app_desc(bk_module, base_manifest)
        observability = ObservabilityConfig.objects.get(module=bk_module)
        assert observability.monitoring is None

    def test_invalid_spec(self, bk_module, manifest):
        manifest["spec"]["observability"] = {
            "monitoring": {"metrics": [{"process": "celery", "serviceName": "metric", "path": "/metrics"}]},
        }

        with pytest.raises(ManifestImportError) as e:
            import_manifest_app_desc(bk_module, manifest)
        assert "not match any process" in str(e)
