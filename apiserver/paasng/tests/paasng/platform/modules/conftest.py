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

import pytest
from django_dynamic_fixture import G

from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
from tests.utils.helpers import generate_random_string


@pytest.fixture()
def image_name():
    return generate_random_string()


@pytest.fixture()
def buildpack(bk_module):
    buildpack = G(AppBuildPack, name="x", region=bk_module.region, language=bk_module.language)
    return buildpack


@pytest.fixture()
def slugbuilder(bk_module, buildpack, image_name):
    slugbuilder = G(AppSlugBuilder, name=image_name, region=bk_module.region)
    slugbuilder.buildpacks.add(buildpack)
    return slugbuilder


@pytest.fixture()
def slugrunner(bk_module, image_name):
    slugrunner = G(AppSlugRunner, name=image_name, region=bk_module.region)
    return slugrunner
