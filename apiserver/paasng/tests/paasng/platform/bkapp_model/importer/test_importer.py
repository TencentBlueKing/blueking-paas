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

import pytest

from paas_wl.bk_app.cnative.specs.constants import ResQuotaPlan, ScalingPolicy
from paas_wl.bk_app.cnative.specs.crd.bk_app import SvcDiscEntryBkSaaS
from paas_wl.bk_app.cnative.specs.models import Mount
from paasng.platform.bkapp_model.importer.exceptions import ManifestImportError
from paasng.platform.bkapp_model.importer.importer import import_manifest
from paasng.platform.bkapp_model.models import ModuleProcessSpec, SvcDiscConfig
from paasng.platform.engine.models.config_var import ConfigVar
from paasng.platform.engine.models.deployment import AutoscalingConfig

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


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
def base_manifest_no_replicas(bk_app):
    """A very basic manifest that can pass the validation, contains no `replicas` field."""
    return {
        "kind": "BkApp",
        "apiVersion": "paas.bk.tencent.com/v1alpha2",
        "metadata": {"name": bk_app.code},
        "spec": {
            "build": {"image": "nginx:latest"},
            "processes": [{"name": "web", "resQuotaPlan": "default"}],
        },
    }


class TestNoReplicas:
    def test_initialization(self, bk_module, base_manifest_no_replicas):
        import_manifest(bk_module, base_manifest_no_replicas)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.target_replicas == 1

    def test_dont_overwrite_existed_value(self, bk_module, base_manifest_no_replicas):
        base_manifest_replicas_3 = copy.deepcopy(base_manifest_no_replicas)
        base_manifest_replicas_3["spec"]["processes"][0]["replicas"] = 3

        import_manifest(bk_module, base_manifest_replicas_3)
        import_manifest(bk_module, base_manifest_no_replicas)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.target_replicas == 3, "The replicas should remain as it is"


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
    import_manifest(bk_module, base_manifest)
    proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
    assert proc_spec.plan_name == ResQuotaPlan.P_DEFAULT.value
    assert proc_spec.scaling_config == AutoscalingConfig(min_replicas=1, max_replicas=2, policy=ScalingPolicy.DEFAULT)


class TestEnvVars:
    def test_invalid_name_input(self, bk_module, base_manifest):
        # Names in lower case are forbidden.
        base_manifest["spec"]["configuration"] = {"env": [{"name": "foo", "value": "foo"}]}
        with pytest.raises(ManifestImportError) as e:
            import_manifest(bk_module, base_manifest)

        assert "configuration.env.0.name" in str(e)

    def test_normal(self, bk_module, base_manifest):
        base_manifest["spec"]["configuration"] = {"env": [{"name": "KEY1", "value": "foo"}]}
        base_manifest["spec"]["envOverlay"] = {"envVariables": [{"envName": "stag", "name": "KEY2", "value": "foo"}]}

        import_manifest(bk_module, base_manifest)
        assert ConfigVar.objects.count() == 2


class TestAddons:
    def test_invalid_value(self, bk_module, base_manifest):
        base_manifest["spec"]["addons"] = [{"foo": "bar"}]
        with pytest.raises(ManifestImportError) as e:
            import_manifest(bk_module, base_manifest)

        assert "addons.0.name" in str(e)

    def test_invalid_spec(self, bk_module, base_manifest):
        base_manifest["spec"]["addons"] = [{"name": "mysql", "specs": [{"foo": "bar"}]}]
        with pytest.raises(ManifestImportError) as e:
            import_manifest(bk_module, base_manifest)

        assert "addons.0.specs" in str(e)

    def test_normal(self, bk_module, base_manifest):
        base_manifest["spec"]["addons"] = [{"name": "mysql"}]
        import_manifest(bk_module, base_manifest)
        # TODO: Add assertion to verify the addons have been imported successfully


class TestMounts:
    def test_invalid_mount_path_input(self, bk_module, base_manifest):
        base_manifest["spec"]["mounts"] = [
            # mountPath must starts with "/"
            {"name": "nginx-conf", "mountPath": "___/etc/nginx", "source": {"configMap": {"name": "nginx-conf-cm"}}}
        ]
        with pytest.raises(ManifestImportError) as e:
            import_manifest(bk_module, base_manifest)

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

        import_manifest(bk_module, base_manifest)
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
            import_manifest(bk_module, base_manifest)

        assert "envOverlay.replicas.0.count" in str(e)

    def test_str(self, bk_module, base_manifest_with_overlay):
        import_manifest(bk_module, base_manifest_with_overlay)
        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.get_target_replicas("stag") == 3

    def test_reset_when_absent_on(self, bk_module, base_manifest, base_manifest_with_overlay):
        import_manifest(bk_module, base_manifest_with_overlay)
        import_manifest(bk_module, base_manifest)

        proc_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert proc_spec.get_target_replicas("stag") == 1, "The overlay data should be reset"

    def test_reset_when_absent_off(self, bk_module, base_manifest, base_manifest_with_overlay):
        import_manifest(bk_module, base_manifest_with_overlay)
        import_manifest(bk_module, base_manifest, reset_overlays_when_absent=False)

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
        import_manifest(bk_module, base_manifest)

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
        import_manifest(bk_module, base_manifest)

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

        import_manifest(bk_module, base_manifest)
        cfg = SvcDiscConfig.objects.get(application=bk_app)

        assert cfg.bk_saas == [
            SvcDiscEntryBkSaaS(bkAppCode="foo"),
            SvcDiscEntryBkSaaS(bkAppCode="bar", moduleName="default"),
            SvcDiscEntryBkSaaS(bkAppCode="bar", moduleName="opps"),
        ]
