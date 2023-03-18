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
from unittest import mock

import cattr
import pytest

from paas_wl.cluster.models import IngressConfig
from paasng.engine.constants import AppEnvName
from paasng.engine.deploy.config import get_env_variables
from paasng.engine.deploy.config.ingress import AppDefaultSubpaths
from paasng.platform.modules.constants import ExposedURLType
from tests.utils.mocks.engine import mock_cluster_service

pytestmark = pytest.mark.django_db


class TestAppDefaultSubpaths:
    @pytest.fixture(autouse=True)
    def setup(self, bk_app):
        module = bk_app.get_default_module()
        module.exposed_url_type = ExposedURLType.SUBPATH
        module.save()
        dummy_ingress_config = cattr.structure(
            {"sub_path_domains": [{"name": "long-example.com"}, {"name": "example.com"}]},
            IngressConfig,
        )
        with mock.patch(
            "paasng.engine.deploy.config.ingress.ModuleEnvSubpaths.get_ingress_config"
        ) as get_ingress_config, mock.patch(
            "paasng.publish.entrance.exposer.get_module_clusters"
        ) as get_module_clusters:
            get_ingress_config.return_value = dummy_ingress_config
            get_module_clusters.return_value = {
                AppEnvName.STAG: mock.MagicMock(ingress_config=dummy_ingress_config),
                AppEnvName.PROD: mock.MagicMock(ingress_config=dummy_ingress_config),
            }
            yield

    @pytest.fixture
    def legacy_sub_path_app(self, bk_app):
        module = bk_app.get_default_module()
        module.exposed_url_type = None
        module.save()
        return bk_app

    @pytest.fixture
    def sub_path_key(self, settings):
        return settings.CONFIGVAR_SYSTEM_PREFIX + "SUB_PATH"

    @pytest.fixture
    def default_subpath_key(self, settings):
        return settings.CONFIGVAR_SYSTEM_PREFIX + "DEFAULT_SUBPATH_ADDRESS"

    @pytest.fixture
    def legacy_style_sub_path(self, bk_stag_env):
        engine_app = bk_stag_env.get_engine_app()
        return f'/{engine_app.region}-{engine_app.name}/'

    @pytest.fixture
    def normal_style_sub_path(self, bk_app):
        return f"/stag--{bk_app.code}/"

    @pytest.mark.parametrize(
        "app, force_legacy_style, expected",
        [
            ("bk_app", False, "normal_style_sub_path"),
            ("bk_app", True, "legacy_style_sub_path"),
            ("legacy_sub_path_app", False, "legacy_style_sub_path"),
            ("legacy_sub_path_app", True, "legacy_style_sub_path"),
        ],
    )
    def test_as_env(
        self,
        request,
        settings,
        sub_path_key,
        default_subpath_key,
        normal_style_sub_path,
        app,
        force_legacy_style,
        expected,
    ):
        bk_app = request.getfixturevalue(app)
        settings.FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE = force_legacy_style
        assert AppDefaultSubpaths(bk_app.get_default_module().get_envs("stag")).as_env_vars() == {
            sub_path_key: request.getfixturevalue(expected),
            # Default SubPath Address is the shortest one in ["fool.com", "foo.com", foobar.com"]
            default_subpath_key: f"http://example.com{normal_style_sub_path}",
        }

    @pytest.mark.parametrize(
        "app, force_legacy_style, expected",
        [
            ("bk_app", False, "normal_style_sub_path"),
            ("bk_app", True, "legacy_style_sub_path"),
            ("legacy_sub_path_app", False, "legacy_style_sub_path"),
            ("legacy_sub_path_app", True, "legacy_style_sub_path"),
        ],
    )
    def test_get_env_variables(
        self,
        request,
        settings,
        sub_path_key,
        app,
        force_legacy_style,
        expected,
    ):
        bk_app = request.getfixturevalue(app)
        settings.FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE = force_legacy_style
        with mock_cluster_service():
            envs = get_env_variables(bk_app.get_default_module().get_envs("stag"))
        assert envs[sub_path_key] == request.getfixturevalue(expected)
