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
from django.utils.crypto import get_random_string
from django_dynamic_fixture import G

from paas_wl.infras.cluster.models import Cluster
from paasng.platform.mgrlegacy.models import CNativeMigrationProcess
from paasng.platform.modules.constants import APP_CATEGORY
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
from tests.conftest import CLUSTER_NAME_FOR_TESTING
from tests.utils.helpers import create_pending_wl_apps

CNATIVE_CLUSTER_NAME = get_random_string(6)


@pytest.fixture(autouse=True)
def _with_wl_apps(bk_app):
    create_pending_wl_apps(bk_app, cluster_name=CLUSTER_NAME_FOR_TESTING)


@pytest.fixture()
def migration_process(bk_app):
    return CNativeMigrationProcess.create_migration_process(bk_app, bk_app.creator)


@pytest.fixture()
def rollback_process(bk_app):
    return CNativeMigrationProcess.create_rollback_process(bk_app, bk_app.creator)


@pytest.fixture(autouse=True)
def _set_default_cluster(settings, bk_app):
    G(Cluster, name=CNATIVE_CLUSTER_NAME, region=bk_app.region)
    G(Cluster, name=CLUSTER_NAME_FOR_TESTING, region=bk_app.region)
    settings.CLOUD_NATIVE_APP_DEFAULT_CLUSTER = CNATIVE_CLUSTER_NAME


@pytest.fixture()
def image_name():
    return get_random_string(6)


@pytest.fixture()
def cnb_image_name():
    return f"cnb{get_random_string(6)}"


@pytest.fixture()
def buildpack(bk_module):
    buildpack = G(AppBuildPack, name=get_random_string(6), region=bk_module.region, language=bk_module.language)
    return buildpack


@pytest.fixture()
def slugbuilder(bk_module, buildpack, image_name):
    slugbuilder = G(
        AppSlugBuilder, name=image_name, region=bk_module.region, labels={APP_CATEGORY.NORMAL_APP.value: "1"}
    )
    slugbuilder.buildpacks.add(buildpack)
    return slugbuilder


@pytest.fixture()
def slugrunner(bk_module, buildpack, image_name):
    return G(AppSlugRunner, name=image_name, region=bk_module.region, labels={APP_CATEGORY.NORMAL_APP.value: "1"})


@pytest.fixture()
def cnb_builder(bk_module, buildpack, cnb_image_name):
    builder = G(
        AppSlugBuilder, name=cnb_image_name, region=bk_module.region, labels={APP_CATEGORY.CNATIVE_APP.value: "1"}
    )
    builder.buildpacks.add(buildpack)
    return builder


@pytest.fixture()
def cnb_runner(bk_module, cnb_image_name):
    return G(AppSlugRunner, name=cnb_image_name, region=bk_module.region, labels={APP_CATEGORY.CNATIVE_APP.value: "1"})


@pytest.fixture()
def _init_runtime(buildpack, slugrunner, slugbuilder, cnb_builder, cnb_runner):
    """"""
