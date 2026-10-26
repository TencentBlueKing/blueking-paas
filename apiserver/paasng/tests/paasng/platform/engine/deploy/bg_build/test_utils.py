# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import base64
import json
from types import SimpleNamespace
from typing import Dict
from unittest import mock

import jwt
import pytest
import urllib3
from django.conf import settings

from paas_wl.bk_app.applications.entities import BuildMetadata
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.utils.text import b64encode
from paas_wl.workloads.images.kres_entities import ImageCredentials
from paas_wl.workloads.images.models import AppImageCredential
from paasng.platform.engine.deploy.bg_build.utils import (
    generate_builder_env_vars,
    generate_slug_path,
    get_envs_from_pypi_url,
    prepare_slugbuilder_template,
    update_env_vars_with_metadata,
)
from tests.paasng.platform.engine.deploy.bg_build.conftest import (
    PLATFORM_PASSWORD,
    PROXY,
    REGISTRY_ALIAS,
    REGISTRY_HOST,
    REGISTRY_NAMESPACE,
    enable_registry_proxy,
    set_cluster_annotations,
)

urllib3.disable_warnings()
pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def user_credential(wl_app) -> AppImageCredential:
    """用户为私有仓库配置的镜像凭证"""
    return AppImageCredential.objects.create(
        app=wl_app,
        registry="private.example.com/foo",
        username="user",
        password="user-pass",
        tenant_id=wl_app.tenant_id,
    )


def _decode_docker_config(value: str) -> Dict:
    return json.loads(base64.b64decode(value))


class TestEnvVars:
    def test_generate_env_vars_without_metadata(self, build_proc, wl_app):
        env_vars = generate_builder_env_vars(build_proc, BuildMetadata(image=""))
        bucket = settings.BLOBSTORE_BUCKET_APP_SOURCE
        cache_path = f"{wl_app.region}/home/{wl_app.name}/cache"
        assert env_vars.pop("TAR_PATH") == f"{bucket}/{build_proc.source_tar_path}", "TAR_PATH 与预期不符"
        assert env_vars.pop("PUT_PATH") == f"{bucket}/{generate_slug_path(build_proc)}", "PUT_PATH 与预期不符"
        assert env_vars.pop("CACHE_PATH") == f"{bucket}/{cache_path}", "CACHE_PATH 与预期不符"
        if settings.BUILD_EXTRA_ENV_VARS:
            for k, v in settings.BUILD_EXTRA_ENV_VARS.items():
                assert env_vars.pop(k) == v, f"{k} 与预期不符"
        if settings.PYTHON_BUILDPACK_PIP_INDEX_URL:
            for k, v in get_envs_from_pypi_url(settings.PYTHON_BUILDPACK_PIP_INDEX_URL).items():
                assert env_vars.pop(k) == v, f"{k} 与预期不符"

    def test_update_env_vars_with_metadata(self, build_proc):
        env: Dict[str, str] = {}
        build_proc.buildpacks = [
            {"type": "git", "url": "https://github.com/x.git", "name": "x", "version": "1.1"},
            {"type": "tar", "url": "https://rgw.com/x.tar", "name": "x", "version": "1.2"},
        ]

        metadata = BuildMetadata(image="", extra_envs={"a": "b"}, buildpacks=build_proc.buildpacks_as_build_env())
        update_env_vars_with_metadata(env, metadata)

        assert metadata.extra_envs["a"] == env["a"]
        assert env["REQUIRED_BUILDPACKS"] == "git x https://github.com/x.git 1.1;tar x https://rgw.com/x.tar 1.2"


@pytest.mark.usefixtures("_platform_registry", "user_credential", "signing_key")
class TestKanikoEnvVarsWithRegistryProxy:
    @pytest.mark.parametrize("enabled", [None, "false", "True"])
    def test_disabled(self, wl_app, build_proc, dockerfile_metadata, enabled):
        if enabled is not None:
            set_cluster_annotations(wl_app, enable_build_registry_proxy=enabled, build_registry_proxy_address=PROXY)

        env_vars = generate_builder_env_vars(build_proc, dockerfile_metadata)

        # 与改造前完全一致
        assert list(env_vars)[:4] == ["SOURCE_GET_URL", "OUTPUT_IMAGE", "CACHE_REPO", "DOCKER_CONFIG_JSON"]
        env_vars.pop("SOURCE_GET_URL")
        expected = {
            "OUTPUT_IMAGE": dockerfile_metadata.image,
            "CACHE_REPO": f"{dockerfile_metadata.image_repository}/dockerbuild-cache",
            "DOCKER_CONFIG_JSON": b64encode(json.dumps(ImageCredentials.load_from_app(wl_app).build_dockerconfig())),
            **settings.BUILD_EXTRA_ENV_VARS,
            **(
                get_envs_from_pypi_url(settings.PYTHON_BUILDPACK_PIP_INDEX_URL)
                if settings.PYTHON_BUILDPACK_PIP_INDEX_URL
                else {}
            ),
            **dockerfile_metadata.extra_envs,
        }
        assert env_vars == expected
        assert REGISTRY_HOST in _decode_docker_config(env_vars["DOCKER_CONFIG_JSON"])["auths"]

    @pytest.mark.parametrize(("skip_tls_verify", "expected_skip_tls"), [("true", PROXY), (None, ""), ("false", "")])
    def test_enabled(self, wl_app, build_proc, dockerfile_metadata, signing_key, skip_tls_verify, expected_skip_tls):
        annos = {} if skip_tls_verify is None else {"build_registry_proxy_skip_tls_verify": skip_tls_verify}
        enable_registry_proxy(wl_app, **annos)
        original_image = dockerfile_metadata.image

        env_vars = generate_builder_env_vars(build_proc, dockerfile_metadata)

        repo_path = f"{REGISTRY_NAMESPACE}/{wl_app.paas_app_code}/{wl_app.module_name}"
        assert env_vars["OUTPUT_IMAGE"] == f"{PROXY}/{REGISTRY_ALIAS}/{repo_path}:main-3f2a1bc"
        assert env_vars["CACHE_REPO"] == f"{PROXY}/{REGISTRY_ALIAS}/{repo_path}/dockerbuild-cache"
        assert env_vars["REGISTRY_MAP"] == f"{REGISTRY_HOST}={PROXY}/{REGISTRY_ALIAS}"
        assert env_vars["SKIP_DEFAULT_REGISTRY_FALLBACK"] == "true"
        # 覆盖 extra_envs 中按平台仓库生成的值
        assert env_vars["SKIP_TLS_VERIFY_REGISTRIES"] == expected_skip_tls
        assert "INSECURE_REGISTRIES" not in env_vars
        # 其他变量保持不变
        assert env_vars["REGISTRY_MIRRORS"] == "mirror.example.com"
        assert env_vars["DOCKERFILE_PATH"] == "Dockerfile"
        # 部署引用的仍是真实仓库地址
        assert dockerfile_metadata.image == original_image

        auths = _decode_docker_config(env_vars["DOCKER_CONFIG_JSON"])["auths"]
        assert set(auths) == {"private.example.com/foo", PROXY}
        assert auths["private.example.com/foo"]["password"] == "user-pass"
        proxy_auth = auths[PROXY]
        token = proxy_auth["password"]
        assert proxy_auth["username"] == "bkpaas-build"
        assert proxy_auth["auth"] == b64encode(f"bkpaas-build:{token}")
        claims = jwt.decode(
            token,
            jwt.PyJWK(signing_key.public_jwk()).key,
            algorithms=["EdDSA"],
            audience=f"bkpaas-registry-proxy:{get_cluster_by_app(wl_app).name}",
        )
        assert claims["push"][0] == {"repo": f"{REGISTRY_ALIAS}/{repo_path}", "tags": ["main-3f2a1bc"]}

        # 构建环境中不存在平台全局仓库账号
        assert all(PLATFORM_PASSWORD not in v for v in env_vars.values())
        assert all(PLATFORM_PASSWORD not in json.dumps(item) for item in auths.values())

    def test_proxy_credential_overrides_user_credential(self, wl_app, build_proc, dockerfile_metadata):
        AppImageCredential.objects.create(
            app=wl_app, registry=PROXY, username="user", password="user-pass", tenant_id=wl_app.tenant_id
        )
        enable_registry_proxy(wl_app)

        env_vars = generate_builder_env_vars(build_proc, dockerfile_metadata)

        assert _decode_docker_config(env_vars["DOCKER_CONFIG_JSON"])["auths"][PROXY]["username"] == "bkpaas-build"

    def test_cnb_build_not_affected(self, wl_app, build_proc):
        enable_registry_proxy(wl_app)
        repo = f"{REGISTRY_HOST}/{REGISTRY_NAMESPACE}/{wl_app.paas_app_code}/{wl_app.module_name}"
        metadata = BuildMetadata(image=f"{repo}:v1", image_repository=repo, use_cnb=True)

        env_vars = generate_builder_env_vars(build_proc, metadata)

        assert env_vars["OUTPUT_IMAGE"] == f"{repo}:v1"
        assert "REGISTRY_MAP" not in env_vars


class TestUtils:
    def test_generate_slug_path(self, wl_app, build_proc):
        slug_path = generate_slug_path(build_proc)
        assert f"{wl_app.region}/home/{wl_app.name}:{build_proc.branch}:{build_proc.revision}/push" == slug_path

    # `get_schedule_config` requires a valid cluster, mock it at this moment
    @mock.patch(
        "paasng.platform.engine.deploy.bg_build.utils.get_schedule_config",
        return_value=SimpleNamespace(
            cluster_name="foo-cluster",
            node_selector={},
            tolerations=[],
        ),
    )
    def test_prepare_slugbuilder_template_without_metadata(self, mocked_, wl_app, build_proc):
        env_vars = generate_builder_env_vars(build_proc, BuildMetadata(image=""))
        slug_tmpl = prepare_slugbuilder_template(wl_app, env_vars, None)
        assert slug_tmpl.name == f"slug-builder--{wl_app.module_name}", (
            "slugbuilder_template 的 name 与app的 name 不一致"
        )
        assert slug_tmpl.namespace == wl_app.namespace, "slugbuilder_template 的namespace 与 app 的 namespace 不一致"
        assert slug_tmpl.runtime.image == settings.DEFAULT_SLUGBUILDER_IMAGE, (
            "slugbuilder_template 的镜像与默认镜像不一致"
        )
        assert slug_tmpl.runtime.envs == env_vars, "slugbuilder_template 的 ConfigVars 与生成的环境变量不一致"

        assert slug_tmpl.schedule.cluster_name == "foo-cluster"
        assert slug_tmpl.schedule.tolerations == []
        assert slug_tmpl.schedule.node_selector == {}


def test_get_envs_from_pypi_url():
    ret = get_envs_from_pypi_url("http://pypi.douban.com")
    assert ret["PIP_INDEX_URL"] == "http://pypi.douban.com"
    assert ret["PIP_INDEX_HOST"] == "pypi.douban.com"
