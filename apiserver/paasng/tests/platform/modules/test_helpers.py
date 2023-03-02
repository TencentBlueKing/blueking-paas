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

import pytest

from paasng.engine.controller.models import Domain
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.exceptions import BindError
from paasng.platform.modules.helpers import (
    ModuleRuntimeBinder,
    ModuleRuntimeManager,
    get_module_clusters,
    get_module_prod_env_root_domains,
)
from tests.utils.helpers import generate_random_string
from tests.utils.mocks.engine import replace_cluster_service

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "slugbuilder_attrs, slugrunner_attrs, ok",
    [
        (dict(name=generate_random_string(12)), dict(name=generate_random_string(16)), False),
        (dict(region=generate_random_string()), dict(), False),
        (dict(), dict(region=generate_random_string()), False),
        (dict(), dict(), True),
    ],
)
def test_bind_image(bk_module, slugbuilder, slugrunner, slugbuilder_attrs, slugrunner_attrs, ok):
    for k, v in slugbuilder_attrs.items():
        setattr(slugbuilder, k, v)
    for k, v in slugrunner_attrs.items():
        setattr(slugrunner, k, v)
    slugbuilder.save()
    slugrunner.save()

    binder = ModuleRuntimeBinder(bk_module, slugbuilder)
    manager = ModuleRuntimeManager(bk_module)
    assert bk_module.slugbuilders.count() == 0
    assert bk_module.slugrunners.count() == 0
    if ok:
        binder.bind_image(slugrunner)
        assert manager.get_slug_builder(raise_exception=True) == slugbuilder
        assert manager.get_slug_runner(raise_exception=True) == slugrunner
        # 测试重复绑定
        binder.bind_image(slugrunner)
        assert bk_module.slugbuilders.count() == 1
        assert bk_module.slugrunners.count() == 1
    else:
        with pytest.raises(BindError):
            binder.bind_image(slugrunner)


@pytest.mark.parametrize(
    "slugbuilder_attrs, buildpack_attrs, linked, ok",
    [
        (dict(name=generate_random_string(12)), dict(name=generate_random_string(16)), False, False),
        (dict(region=generate_random_string()), dict(), False, False),
        (dict(), dict(region=generate_random_string()), False, False),
        (dict(name=generate_random_string(12)), dict(name=generate_random_string(16)), True, True),
        (dict(region=generate_random_string()), dict(), True, False),
        (dict(), dict(region=generate_random_string()), True, False),
        (dict(), dict(), True, True),
    ],
)
def test_bind_buildpack(bk_module, slugbuilder, buildpack, slugbuilder_attrs, buildpack_attrs, linked, ok):
    for k, v in slugbuilder_attrs.items():
        setattr(slugbuilder, k, v)
    for k, v in buildpack_attrs.items():
        setattr(buildpack, k, v)
    slugbuilder.buildpacks.clear()
    slugbuilder.save()
    buildpack.save()

    binder = ModuleRuntimeBinder(bk_module, slugbuilder)
    manager = ModuleRuntimeManager(bk_module)

    assert bk_module.slugbuilders.count() == 0
    assert bk_module.buildpacks.count() == 0
    assert slugbuilder.buildpacks.count() == 0

    if linked:
        slugbuilder.buildpacks.add(buildpack)
        assert slugbuilder.buildpacks.count() == 1

    if ok:
        binder.bind_buildpack(buildpack)
        assert manager.get_slug_builder(raise_exception=True) == slugbuilder
        assert manager.list_buildpacks() == [buildpack]
        # 测试重复绑定
        binder.bind_buildpack(buildpack)
        assert bk_module.buildpacks.count() == 1

    else:
        with pytest.raises(BindError):
            binder.bind_buildpack(buildpack)


def test_get_module_clusters(bk_module):
    with replace_cluster_service():
        assert len(get_module_clusters(bk_module)) != 0


def test_get_module_clusters_engineless(bk_module):
    bk_module.envs.all().delete()
    assert len(get_module_clusters(bk_module)) == 0


@pytest.mark.parametrize(
    'exposed_url_type, ingress_config, include_reserved, expected_domains',
    [
        (
            ExposedURLType.SUBDOMAIN,
            {'app_root_domains': [{'name': 'foo.com'}, {'name': 'bar.com'}]},
            False,
            [Domain('foo.com'), Domain('bar.com')],
        ),
        (
            ExposedURLType.SUBDOMAIN,
            {'app_root_domains': [{'name': 'foo.com'}, {'name': 'bar.com', 'reserved': True}]},
            False,
            [Domain('foo.com')],
        ),
        (
            ExposedURLType.SUBDOMAIN,
            {'app_root_domains': [{'name': 'foo.com'}, {'name': 'bar.com', 'reserved': True}]},
            True,
            [Domain('foo.com'), Domain('bar.com', reserved=True)],
        ),
        (
            ExposedURLType.SUBPATH,
            {'sub_path_domains': [{'name': 'foo.com'}, {'name': 'bar.com'}]},
            False,
            [Domain('foo.com'), Domain('bar.com')],
        ),
    ],
)
def test_get_module_prod_env_root_domains(
    bk_module, exposed_url_type, ingress_config, include_reserved, expected_domains
):
    with replace_cluster_service(replaced_ingress_config=ingress_config):
        bk_module.exposed_url_type = exposed_url_type
        assert get_module_prod_env_root_domains(bk_module, include_reserved) == expected_domains
