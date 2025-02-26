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

from operator import attrgetter
from textwrap import dedent

import pytest
import yaml
from django_dynamic_fixture import G

from paasng.platform.applications.constants import AppLanguage
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities.proc_env_overlays import ReplicasOverlay
from paasng.platform.bkapp_model.entities.v1alpha2 import BkAppSpec
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import _adjust_desc_replicas, get_deploy_desc_handler, get_desc_handler
from paasng.utils.structure import NotSetType

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGetAppDescHandlerIncorrectVersions:
    def test_ver_1(self, bk_user):
        yaml_content = dedent(
            """
        app_code: foo
        app_name: foo
        """
        )

        with pytest.raises(DescriptionValidationError, match='version "1" is not supported'):
            get_desc_handler(yaml.safe_load(yaml_content)).handle_app(bk_user)

    def test_ver_unspecified(self, bk_user):
        yaml_content = dedent(
            """
        bk_app_code: foo
        bk_app_name: foo
        """
        )

        with pytest.raises(DescriptionValidationError, match="No spec version is specified"):
            get_desc_handler(yaml.safe_load(yaml_content)).handle_app(bk_user)

    def test_ver_unknown_number(self, bk_user):
        yaml_content = "spec_version: 999"

        with pytest.raises(DescriptionValidationError, match='version "999" is not supported'):
            get_desc_handler(yaml.safe_load(yaml_content)).handle_app(bk_user)

    def test_ver_unknown_string(self, bk_user):
        yaml_content = "spec_version: foobar"

        with pytest.raises(DescriptionValidationError, match='version "foobar" is not supported'):
            get_desc_handler(yaml.safe_load(yaml_content)).handle_app(bk_user)


class TestGetDeployDescHandlerIncorrectVersions:
    def test_ver_1(self, bk_user):
        yaml_content = dedent(
            """
        app_code: foo
        app_name: foo
        """
        )

        with pytest.raises(ValueError, match='version "1" is not supported'):
            get_deploy_desc_handler(yaml.safe_load(yaml_content))

    def test_ver_unspecified(self, bk_user):
        yaml_content = dedent(
            """
        bk_app_code: foo
        bk_app_name: foo
        """
        )

        with pytest.raises(ValueError, match="no spec version is specified"):
            get_deploy_desc_handler(yaml.safe_load(yaml_content))

    def test_ver_unknown_number(self, bk_user):
        yaml_content = "spec_version: 999"

        with pytest.raises(ValueError, match='version "999" is not supported'):
            get_deploy_desc_handler(yaml.safe_load(yaml_content))

    def test_ver_unknown_string(self, bk_user):
        yaml_content = "spec_version: foobar"

        with pytest.raises(ValueError, match='version "foobar" is not supported'):
            get_deploy_desc_handler(yaml.safe_load(yaml_content))


class Test__adjust_desc_replicas:
    def test(self, bk_stag_env):
        """测试场景: 首次部署"""

        # without spec.env_overlay.replicas
        desc = DeploymentDesc(language=AppLanguage.PYTHON, spec=BkAppSpec(processes=[{"name": "web", "replicas": 5}]))
        _adjust_desc_replicas(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == 5
        assert isinstance(desc.spec.env_overlay, NotSetType)

        # with spec.env_overlay.replicas
        desc = DeploymentDesc(
            language=AppLanguage.PYTHON,
            spec=BkAppSpec(
                processes=[{"name": "web", "replicas": 2}],
                env_overlay={
                    "replicas": [
                        {"count": 10, "env_name": "stag", "process": "web"},
                        {"count": 20, "env_name": "prod", "process": "web"},
                    ]
                },
            ),
        )
        _adjust_desc_replicas(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == 2
        assert desc.spec.env_overlay.replicas == [  # type: ignore[union-attr]
            ReplicasOverlay(count=10, env_name="stag", process="web"),
            ReplicasOverlay(count=20, env_name="prod", process="web"),
        ]

    def test_after_scale_stag(self, bk_stag_env):
        """测试场景: 通过页面对 stag 环境做了扩缩容后再次部署"""
        stag_online_replicas = 3
        online_replicas = 5
        proc_spec = G(
            ModuleProcessSpec,
            module=bk_stag_env.module,
            name="web",
            command=["python"],
            target_replicas=online_replicas,
        )
        G(ProcessSpecEnvOverlay, proc_spec=proc_spec, target_replicas=stag_online_replicas, environment_name="stag")
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_overlay_replicas("web", "stag")).set(
            fieldmgr.FieldMgrName.WEB_FORM
        )
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_proc_replicas("web")).set(fieldmgr.FieldMgrName.APP_DESC)

        # without spec.env_overlay.replicas
        desc = DeploymentDesc(language=AppLanguage.PYTHON, spec=BkAppSpec(processes=[{"name": "web", "replicas": 10}]))
        _adjust_desc_replicas(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        assert isinstance(desc.spec.env_overlay, NotSetType)

        # with spec.env_overlay.replicas
        desc = DeploymentDesc(
            language=AppLanguage.PYTHON,
            spec=BkAppSpec(
                processes=[{"name": "web", "replicas": 10}],
                env_overlay={
                    "replicas": [
                        {"count": 15, "env_name": "stag", "process": "web"},
                        {"count": 25, "env_name": "prod", "process": "web"},
                    ]
                },
            ),
        )

        _adjust_desc_replicas(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        assert isinstance(desc.spec.env_overlay.replicas, NotSetType)  # type: ignore[union-attr]

        desc = DeploymentDesc(
            language=AppLanguage.PYTHON,
            spec=BkAppSpec(
                processes=[{"name": "web", "replicas": 10}],
                env_overlay={
                    "replicas": [
                        {"count": 25, "env_name": "prod", "process": "web"},
                    ]
                },
            ),
        )

        _adjust_desc_replicas(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        assert isinstance(desc.spec.env_overlay.replicas, NotSetType)  # type: ignore[union-attr]

    def test_after_scale_all(self, bk_stag_env):
        """测试场景: 通过页面对 stag/prod 两个环境做了扩缩容后再次部署"""
        stag_online_replicas = 3
        prod_online_replicas = 5
        proc_spec = G(
            ModuleProcessSpec,
            module=bk_stag_env.module,
            name="web",
            command=["python"],
            target_replicas=1,
        )
        G(ProcessSpecEnvOverlay, proc_spec=proc_spec, target_replicas=stag_online_replicas, environment_name="stag")
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_overlay_replicas("web", "stag")).set(
            fieldmgr.FieldMgrName.WEB_FORM
        )
        G(ProcessSpecEnvOverlay, proc_spec=proc_spec, target_replicas=prod_online_replicas, environment_name="prod")
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_overlay_replicas("web", "prod")).set(
            fieldmgr.FieldMgrName.WEB_FORM
        )

        # without spec.env_overlay.replicas
        desc = DeploymentDesc(language=AppLanguage.PYTHON, spec=BkAppSpec(processes=[{"name": "web", "replicas": 10}]))
        _adjust_desc_replicas(desc, bk_stag_env)
        assert isinstance(desc.spec.env_overlay, NotSetType)

        # with spec.env_overlay.replicas
        desc = DeploymentDesc(
            language=AppLanguage.PYTHON,
            spec=BkAppSpec(
                processes=[{"name": "web", "replicas": 10}],
                env_overlay={
                    "replicas": [
                        {"count": 15, "env_name": "stag", "process": "web"},
                        {"count": 25, "env_name": "prod", "process": "web"},
                    ]
                },
            ),
        )
        _adjust_desc_replicas(desc, bk_stag_env)
        assert isinstance(desc.spec.env_overlay.replicas, NotSetType)  # type: ignore[union-attr]

    def test_after_set_with_proc_replicas(self, bk_stag_env):
        """测试场景: 仅通过 app_desc 更新副本数(不区分环境)"""
        online_replicas = 5
        G(
            ModuleProcessSpec,
            module=bk_stag_env.module,
            name="web",
            command=["python"],
            target_replicas=online_replicas,
        )
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_proc_replicas("web")).set(fieldmgr.FieldMgrName.APP_DESC)

        # without spec.env_overlay.replicas
        desc = DeploymentDesc(language=AppLanguage.PYTHON, spec=BkAppSpec(processes=[{"name": "web", "replicas": 10}]))
        _adjust_desc_replicas(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        assert isinstance(desc.spec.env_overlay, NotSetType)

        # with spec.env_overlay.replicas
        desc = DeploymentDesc(
            language=AppLanguage.PYTHON,
            spec=BkAppSpec(
                processes=[{"name": "web", "replicas": 10}],
                env_overlay={
                    "replicas": [
                        {"count": 15, "env_name": "stag", "process": "web"},
                        {"count": 25, "env_name": "prod", "process": "web"},
                    ]
                },
            ),
        )
        _adjust_desc_replicas(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        assert isinstance(desc.spec.env_overlay.replicas, NotSetType)  # type: ignore[union-attr]

    def test_after_set_with_env_overlay_stag(self, bk_stag_env):
        """测试场景: 通过 spec.env_overlay.replicas['stag'] 更新过副本数后再次部署"""
        stag_online_replicas = 3
        online_replicas = 2
        proc_spec = G(
            ModuleProcessSpec,
            module=bk_stag_env.module,
            name="web",
            command=["python"],
            target_replicas=2,
        )
        G(ProcessSpecEnvOverlay, proc_spec=proc_spec, target_replicas=stag_online_replicas, environment_name="stag")
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_proc_replicas("web")).set(fieldmgr.FieldMgrName.APP_DESC)
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_overlay_replicas("web", "stag")).set(
            fieldmgr.FieldMgrName.APP_DESC
        )

        # without spec.env_overlay.replicas
        desc = DeploymentDesc(language=AppLanguage.PYTHON, spec=BkAppSpec(processes=[{"name": "web", "replicas": 10}]))
        _adjust_desc_replicas(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        assert desc.spec.env_overlay.replicas == [  # type: ignore[union-attr]
            ReplicasOverlay(env_name="stag", process="web", count=stag_online_replicas)
        ]

        # with spec.env_overlay.replicas
        desc = DeploymentDesc(
            language=AppLanguage.PYTHON,
            spec=BkAppSpec(
                processes=[{"name": "web", "replicas": 10}],
                env_overlay={
                    "replicas": [
                        {"count": 15, "env_name": "stag", "process": "web"},
                        {"count": 25, "env_name": "prod", "process": "web"},
                    ]
                },
            ),
        )
        _adjust_desc_replicas(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        assert desc.spec.env_overlay.replicas == [  # type: ignore[union-attr]
            ReplicasOverlay(env_name="stag", process="web", count=stag_online_replicas)
        ]

    def test_after_set_with_env_overlay(self, bk_stag_env):
        """测试场景: 通过 spec.env_overlay.replicas 更新过副本数后再次部署"""
        stag_online_replicas = 3
        prod_online_replicas = 2
        proc_spec = G(
            ModuleProcessSpec,
            module=bk_stag_env.module,
            name="web",
            command=["python"],
            target_replicas=2,
        )
        G(ProcessSpecEnvOverlay, proc_spec=proc_spec, target_replicas=stag_online_replicas, environment_name="stag")
        G(ProcessSpecEnvOverlay, proc_spec=proc_spec, target_replicas=prod_online_replicas, environment_name="prod")
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_overlay_replicas("web", "stag")).set(
            fieldmgr.FieldMgrName.APP_DESC
        )
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_overlay_replicas("web", "prod")).set(
            fieldmgr.FieldMgrName.APP_DESC
        )

        # without spec.env_overlay.replicas
        desc = DeploymentDesc(language=AppLanguage.PYTHON, spec=BkAppSpec(processes=[{"name": "web", "replicas": 10}]))
        _adjust_desc_replicas(desc, bk_stag_env)
        assert sorted(desc.spec.env_overlay.replicas, key=attrgetter("env_name"), reverse=True) == [  # type: ignore[union-attr, arg-type]
            ReplicasOverlay(env_name="stag", process="web", count=stag_online_replicas),
            ReplicasOverlay(env_name="prod", process="web", count=prod_online_replicas),
        ]

        # with spec.env_overlay.replicas
        desc = DeploymentDesc(
            language=AppLanguage.PYTHON,
            spec=BkAppSpec(
                processes=[{"name": "web", "replicas": 10}],
                env_overlay={
                    "replicas": [
                        {"count": 15, "env_name": "stag", "process": "web"},
                        {"count": 25, "env_name": "prod", "process": "web"},
                    ]
                },
            ),
        )
        _adjust_desc_replicas(desc, bk_stag_env)
        assert sorted(desc.spec.env_overlay.replicas, key=attrgetter("env_name"), reverse=True) == [  # type: ignore[union-attr, arg-type]
            ReplicasOverlay(env_name="stag", process="web", count=stag_online_replicas),
            ReplicasOverlay(env_name="prod", process="web", count=prod_online_replicas),
        ]

        desc = DeploymentDesc(
            language=AppLanguage.PYTHON,
            spec=BkAppSpec(
                processes=[{"name": "web", "replicas": 10}],
                env_overlay={
                    "replicas": [
                        {"count": 25, "env_name": "prod", "process": "web"},
                    ]
                },
            ),
        )
        _adjust_desc_replicas(desc, bk_stag_env)
        assert sorted(desc.spec.env_overlay.replicas, key=attrgetter("env_name"), reverse=True) == [  # type: ignore[union-attr, arg-type]
            ReplicasOverlay(env_name="stag", process="web", count=stag_online_replicas),
            ReplicasOverlay(env_name="prod", process="web", count=prod_online_replicas),
        ]
