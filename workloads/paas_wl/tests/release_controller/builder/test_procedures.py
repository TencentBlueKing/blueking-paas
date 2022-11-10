# -*- coding: utf-8 -*-
from typing import Dict

from django.conf import settings
from django.test import TestCase

from paas_wl.platform.applications.models.managers.app_configvar import AppConfigVarManager
from paas_wl.release_controller.builder.procedures import (
    generate_builder_env_vars,
    generate_slug_path,
    prepare_slugbuilder_template,
    update_env_vars_with_metadata,
)
from paas_wl.release_controller.builder.utils import get_envs_for_pypi
from paas_wl.resources.utils.basic import get_full_node_selector
from tests.utils.app import random_fake_app
from tests.utils.build_process import random_fake_bp


class TestEnvVars(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = random_fake_app()
        self.bp = random_fake_bp(self.app)

    def test_generate_env_vars_without_metadata(self):
        env_vars = generate_builder_env_vars(self.bp, {})
        bucket = settings.BLOBSTORE_S3_BUCKET_NAME
        cache_path = f'{self.app.region}/home/{self.app.name}/cache'
        assert env_vars.pop("TAR_PATH") == f"{bucket}/{self.bp.source_tar_path}", "TAR_PATH 与预期不符"
        assert env_vars.pop("PUT_PATH") == f"{bucket}/{generate_slug_path(self.bp)}", "PUT_PATH 与预期不符"
        assert env_vars.pop("CACHE_PATH") == f"{bucket}/{cache_path}", "CACHE_PATH 与预期不符"
        if settings.BUILD_EXTRA_ENV_VARS:
            for k, v in settings.BUILD_EXTRA_ENV_VARS.items():
                assert env_vars.pop(k) == v, f"{k} 与预期不符"
        if settings.PYTHON_BUILDPACK_PIP_INDEX_URL:
            for k, v in get_envs_for_pypi(settings.PYTHON_BUILDPACK_PIP_INDEX_URL).items():
                assert env_vars.pop(k) == v, f"{k} 与预期不符"
        app_config_var = AppConfigVarManager(app=self.app).get_envs()
        for key in app_config_var.keys() & env_vars.keys():
            assert env_vars[key] == app_config_var[key], f"{key} 与预期不符"

    def test_update_env_vars_with_metadata(self):
        env: Dict[str, str] = {}
        self.bp.buildpacks = [
            {"type": "git", "url": "https://github.com/x.git", "name": "x", "version": "1.1"},
            {"type": "tar", "url": "https://rgw.com/x.tar", "name": "x", "version": "1.2"},
        ]

        metadata = {"extra_envs": {"a": "b"}, "buildpacks": self.bp.buildpacks_as_build_env()}
        update_env_vars_with_metadata(env, metadata)

        assert metadata["extra_envs"]["a"] == env["a"]
        print(env["REQUIRED_BUILDPACKS"])
        assert "git x https://github.com/x.git 1.1;tar x https://rgw.com/x.tar 1.2" == env["REQUIRED_BUILDPACKS"]


class TestUtils(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = random_fake_app()
        self.bp = random_fake_bp(self.app)

    def test_generate_slug_path(self):
        app = self.app
        bp = self.bp
        slug_path = generate_slug_path(self.bp)
        assert f'{app.region}/home/{app.name}:{bp.branch}:{bp.revision}/push' == slug_path

    def test_prepare_slugbuilder_template_without_metadata(self):
        env_vars = generate_builder_env_vars(self.bp, {})
        slugbuilder_template = prepare_slugbuilder_template(self.app, env_vars, {})
        assert slugbuilder_template.name == "slug-builder", "slugbuilder_template 的 name 与app的 name 不一致"
        assert slugbuilder_template.namespace == self.app.namespace, "slugbuilder_template 的namespace与app的namespace不一致"
        assert (
            slugbuilder_template.runtime.image == settings.DEFAULT_SLUGBUILDER_IMAGE
        ), "slugbuilder_template 的镜像与默认镜像不一致"
        assert slugbuilder_template.runtime.envs == env_vars, "slugbuilder_template 的ConfigVars与生成的环境变量不一致"
        assert slugbuilder_template.schedule.node_selector == get_full_node_selector(
            self.app
        ), "slugbuilder_template 的节点选择器参数异常"
        assert (
            slugbuilder_template.schedule.tolerations == self.app.latest_config.tolerations
        ), "slugbuilder_template 的 tolerations 与app关联的config.tolerations 不一致"
