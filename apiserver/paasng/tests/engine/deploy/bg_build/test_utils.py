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
from types import SimpleNamespace
from typing import Dict
from unittest import mock

import pytest
import urllib3
from django.conf import settings

from paas_wl.platform.applications.models.managers.app_configvar import AppConfigVarManager
from paasng.engine.deploy.bg_build.utils import (
    generate_builder_env_vars,
    generate_slug_path,
    get_envs_from_pypi_url,
    prepare_slugbuilder_template,
    update_env_vars_with_metadata,
)

urllib3.disable_warnings()
pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


class TestEnvVars:
    def test_generate_env_vars_without_metadata(self, build_proc, wl_app):
        env_vars = generate_builder_env_vars(build_proc, {})
        bucket = settings.BLOBSTORE_BUCKET_APP_SOURCE
        cache_path = f'{wl_app.region}/home/{wl_app.name}/cache'
        assert env_vars.pop("TAR_PATH") == f"{bucket}/{build_proc.source_tar_path}", "TAR_PATH 与预期不符"
        assert env_vars.pop("PUT_PATH") == f"{bucket}/{generate_slug_path(build_proc)}", "PUT_PATH 与预期不符"
        assert env_vars.pop("CACHE_PATH") == f"{bucket}/{cache_path}", "CACHE_PATH 与预期不符"
        if settings.BUILD_EXTRA_ENV_VARS:
            for k, v in settings.BUILD_EXTRA_ENV_VARS.items():
                assert env_vars.pop(k) == v, f"{k} 与预期不符"
        if settings.PYTHON_BUILDPACK_PIP_INDEX_URL:
            for k, v in get_envs_from_pypi_url(settings.PYTHON_BUILDPACK_PIP_INDEX_URL).items():
                assert env_vars.pop(k) == v, f"{k} 与预期不符"
        app_config_var = AppConfigVarManager(app=wl_app).get_envs()
        for key in app_config_var.keys() & env_vars.keys():
            assert env_vars[key] == app_config_var[key], f"{key} 与预期不符"

    def test_update_env_vars_with_metadata(self, build_proc):
        env: Dict[str, str] = {}
        build_proc.buildpacks = [
            {"type": "git", "url": "https://github.com/x.git", "name": "x", "version": "1.1"},
            {"type": "tar", "url": "https://rgw.com/x.tar", "name": "x", "version": "1.2"},
        ]

        metadata = {"extra_envs": {"a": "b"}, "buildpacks": build_proc.buildpacks_as_build_env()}
        update_env_vars_with_metadata(env, metadata)

        assert metadata["extra_envs"]["a"] == env["a"]
        print(env["REQUIRED_BUILDPACKS"])
        assert "git x https://github.com/x.git 1.1;tar x https://rgw.com/x.tar 1.2" == env["REQUIRED_BUILDPACKS"]


class TestUtils:
    def test_generate_slug_path(self, wl_app, build_proc):
        slug_path = generate_slug_path(build_proc)
        assert f'{wl_app.region}/home/{wl_app.name}:{build_proc.branch}:{build_proc.revision}/push' == slug_path

    # `get_schedule_config` requires a valid cluster, mock it at this moment
    @mock.patch(
        'paasng.engine.deploy.bg_build.utils.get_schedule_config',
        return_value=SimpleNamespace(
            cluster_name='foo-cluster',
            node_selector={},
            tolerations=[],
        ),
    )
    def test_prepare_slugbuilder_template_without_metadata(self, _, wl_app, build_proc):
        env_vars = generate_builder_env_vars(build_proc, {})
        slug_tmpl = prepare_slugbuilder_template(wl_app, env_vars, {})
        assert slug_tmpl.name == "slug-builder", "slugbuilder_template 的 name 与app的 name 不一致"
        assert slug_tmpl.namespace == wl_app.namespace, "slugbuilder_template 的namespace与app的namespace不一致"
        assert slug_tmpl.runtime.image == settings.DEFAULT_SLUGBUILDER_IMAGE, "slugbuilder_template 的镜像与默认镜像不一致"
        assert slug_tmpl.runtime.envs == env_vars, "slugbuilder_template 的ConfigVars与生成的环境变量不一致"

        assert slug_tmpl.schedule.cluster_name == 'foo-cluster'
        assert slug_tmpl.schedule.tolerations == []
        assert slug_tmpl.schedule.node_selector == {}


def test_get_envs_from_pypi_url():
    ret = get_envs_from_pypi_url('http://pypi.douban.com')
    assert ret['PIP_INDEX_URL'] == 'http://pypi.douban.com'
    assert ret['PIP_INDEX_HOST'] == 'pypi.douban.com'
