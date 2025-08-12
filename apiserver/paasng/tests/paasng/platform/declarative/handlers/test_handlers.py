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
from paasng.platform.bkapp_model.entities.v1alpha2 import BkAppEnvOverlay, BkAppSpec
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import (
    apply_form_replicas_overrides,
    get_deploy_desc_handler,
    get_desc_handler,
)
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


class Test__apply_form_replicas_overrides:
    def test(self, bk_stag_env):
        """测试场景: 首次部署"""
        new_replicas = 5

        # without spec.env_overlay.replicas
        desc = self._make_desc(new_replicas)
        apply_form_replicas_overrides(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == new_replicas
        self._assert_is_notset(desc.spec.env_overlay)

        # with spec.env_overlay.replicas
        overlay_replicas = self.make_overlay_replicas(new_replicas, new_replicas * 2)
        desc = self._make_desc(new_replicas, overlay_replicas=overlay_replicas)
        apply_form_replicas_overrides(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == new_replicas
        assert desc.spec.env_overlay.replicas == overlay_replicas

    @pytest.mark.parametrize(("env_name", "online_replicas"), [("stag", 3), ("prod", 5)])
    def test_after_scale_single_env(self, bk_stag_env, bk_prod_env, env_name, online_replicas):
        """测试场景: 通过页面对 stag 或 prod 环境做了扩缩容后再次部署"""
        proc_spec = G(
            ModuleProcessSpec,
            module=bk_stag_env.module,
            name="web",
            command=["python"],
            target_replicas=online_replicas,
        )
        G(ProcessSpecEnvOverlay, proc_spec=proc_spec, target_replicas=online_replicas, environment_name=env_name)
        fieldmgr.MultiFieldsManager(bk_stag_env.module).set_many(
            [fieldmgr.f_overlay_replicas("web", env_name), fieldmgr.f_proc_replicas("web")],
            fieldmgr.FieldMgrName.WEB_FORM,
        )

        new_replicas = 10

        # without spec.env_overlay.replicas
        desc = self._make_desc(new_replicas)
        apply_form_replicas_overrides(desc, bk_stag_env)
        self._assert_is_notset(desc.spec.processes[0].replicas)
        self._assert_is_notset(desc.spec.env_overlay)

        # with spec.env_overlay.replicas
        desc = self._make_desc(
            new_replicas, overlay_replicas=self.make_overlay_replicas(new_replicas, new_replicas * 2)
        )
        apply_form_replicas_overrides(desc, bk_stag_env)
        self._assert_is_notset(desc.spec.processes[0].replicas)
        self._assert_is_notset(desc.spec.env_overlay.replicas)

        desc = self._make_desc(
            new_replicas,
            overlay_replicas=self.make_overlay_replicas_by_env("prod", new_replicas * 2),
        )
        apply_form_replicas_overrides(desc, bk_stag_env)
        self._assert_is_notset(desc.spec.processes[0].replicas)
        self._assert_is_notset(desc.spec.env_overlay.replicas)

    def test_after_scale_all_env(self, bk_stag_env):
        """测试场景: 通过页面同时对 stag 和 prod 两个环境做了扩缩容后再次部署"""
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
        G(ProcessSpecEnvOverlay, proc_spec=proc_spec, target_replicas=prod_online_replicas, environment_name="prod")
        fieldmgr.MultiFieldsManager(bk_stag_env.module).set_many(
            [
                fieldmgr.f_overlay_replicas("web", "stag"),
                fieldmgr.f_overlay_replicas("web", "prod"),
                fieldmgr.f_proc_replicas("web"),
            ],
            fieldmgr.FieldMgrName.WEB_FORM,
        )

        new_replicas = 10

        # without spec.env_overlay.replicas
        desc = self._make_desc(new_replicas)
        apply_form_replicas_overrides(desc, bk_stag_env)
        self._assert_is_notset(desc.spec.processes[0].replicas)
        self._assert_is_notset(desc.spec.env_overlay)

        # with spec.env_overlay.replicas
        desc = self._make_desc(
            new_replicas,
            overlay_replicas=self.make_overlay_replicas(new_replicas, new_replicas * 2),
        )
        apply_form_replicas_overrides(desc, bk_stag_env)
        self._assert_is_notset(desc.spec.processes[0].replicas)
        self._assert_is_notset(desc.spec.env_overlay.replicas)

    def test_after_set_with_proc_replicas(self, bk_stag_env):
        """测试场景: 仅通过 app_desc 更新副本数(不区分环境)后再次部署"""
        online_replicas = 5
        G(
            ModuleProcessSpec,
            module=bk_stag_env.module,
            name="web",
            command=["python"],
            target_replicas=online_replicas,
        )
        fieldmgr.FieldManager(bk_stag_env.module, fieldmgr.f_proc_replicas("web")).set(fieldmgr.FieldMgrName.APP_DESC)

        new_replicas = 10

        # without spec.env_overlay.replicas
        desc = self._make_desc(new_replicas)
        apply_form_replicas_overrides(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        self._assert_is_notset(desc.spec.env_overlay)

        # with spec.env_overlay.replicas
        desc = self._make_desc(
            new_replicas,
            overlay_replicas=self.make_overlay_replicas(new_replicas, new_replicas * 2),
        )
        apply_form_replicas_overrides(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        self._assert_is_notset(desc.spec.env_overlay.replicas)

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
        fieldmgr.MultiFieldsManager(bk_stag_env.module).set_many(
            [fieldmgr.f_proc_replicas("web"), fieldmgr.f_overlay_replicas("web", "stag")],
            fieldmgr.FieldMgrName.APP_DESC,
        )

        new_replicas = 10

        # without spec.env_overlay.replicas
        desc = self._make_desc(new_replicas)
        apply_form_replicas_overrides(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        assert desc.spec.env_overlay.replicas == self.make_overlay_replicas_by_env("stag", stag_online_replicas)

        # with spec.env_overlay.replicas
        desc = self._make_desc(
            new_replicas,
            overlay_replicas=self.make_overlay_replicas(new_replicas, new_replicas * 2),
        )
        apply_form_replicas_overrides(desc, bk_stag_env)
        assert desc.spec.processes[0].replicas == online_replicas
        assert desc.spec.env_overlay.replicas == self.make_overlay_replicas_by_env("stag", stag_online_replicas)

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
        fieldmgr.MultiFieldsManager(bk_stag_env.module).set_many(
            [fieldmgr.f_overlay_replicas("web", "stag"), fieldmgr.f_overlay_replicas("web", "prod")],
            fieldmgr.FieldMgrName.APP_DESC,
        )

        online_env_overlay_replicas = self.make_overlay_replicas(stag_online_replicas, prod_online_replicas)

        new_replicas = 10

        # without spec.env_overlay.replicas
        desc = self._make_desc(new_replicas)
        apply_form_replicas_overrides(desc, bk_stag_env)
        assert (
            sorted(desc.spec.env_overlay.replicas, key=attrgetter("env_name"), reverse=True)
            == online_env_overlay_replicas
        )

        # with spec.env_overlay.replicas
        desc = self._make_desc(
            new_replicas,
            overlay_replicas=self.make_overlay_replicas(new_replicas, new_replicas * 2),
        )
        apply_form_replicas_overrides(desc, bk_stag_env)
        assert (
            sorted(desc.spec.env_overlay.replicas, key=attrgetter("env_name"), reverse=True)
            == online_env_overlay_replicas
        )

        desc = self._make_desc(
            new_replicas,
            overlay_replicas=self.make_overlay_replicas_by_env("prod", new_replicas * 2),
        )
        apply_form_replicas_overrides(desc, bk_stag_env)
        assert (
            sorted(desc.spec.env_overlay.replicas, key=attrgetter("env_name"), reverse=True)
            == online_env_overlay_replicas
        )

    @staticmethod
    def _make_desc(new_replicas, overlay_replicas=None):
        desc = DeploymentDesc(
            language=AppLanguage.PYTHON, spec=BkAppSpec(processes=[{"name": "web", "replicas": new_replicas}])
        )
        if overlay_replicas:
            desc.spec.env_overlay = BkAppEnvOverlay(replicas=overlay_replicas)
        return desc

    @staticmethod
    def make_overlay_replicas(stag_replicas, prod_replicas):
        return [
            ReplicasOverlay(env_name="stag", process="web", count=stag_replicas),
            ReplicasOverlay(env_name="prod", process="web", count=prod_replicas),
        ]

    @staticmethod
    def make_overlay_replicas_by_env(env_name, replicas):
        return [
            ReplicasOverlay(env_name=env_name, process="web", count=replicas),
        ]

    @staticmethod
    def _assert_is_notset(test_data):
        assert isinstance(test_data, NotSetType)
