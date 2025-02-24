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

from paas_wl.infras.cluster.shim import Cluster, EnvClusterService
from paasng.platform.modules.constants import ExposedURLType

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.usefixtures("_with_wl_apps"),
]


@pytest.fixture(autouse=True)
def _setup(settings):
    """setup clusters and wl_apps"""
    Cluster.objects.all().delete()
    G(
        Cluster,
        name="default",
        is_default=True,
        exposed_url_type=ExposedURLType.SUBDOMAIN.value,
        region=settings.DEFAULT_REGION_NAME,
    )
    G(Cluster, name="extra-1", is_default=False, region=settings.DEFAULT_REGION_NAME)


class TestEnvClusterService:
    def test_empty_cluster_field(self, bk_stag_env):
        wl_app = bk_stag_env.wl_app
        latest_config = wl_app.latest_config
        latest_config.cluster = ""
        latest_config.save()
        wl_app.refresh_from_db()
        assert EnvClusterService(bk_stag_env).get_cluster().name == "default"

    def test_valid_cluster_field(self, bk_stag_env):
        wl_app = bk_stag_env.wl_app
        latest_config = wl_app.latest_config
        latest_config.cluster = "extra-1"
        latest_config.save()
        wl_app.refresh_from_db()
        assert EnvClusterService(bk_stag_env).get_cluster().name == "extra-1"

    def test_invalid_cluster_field(self, bk_stag_env):
        wl_app = bk_stag_env.wl_app
        latest_config = wl_app.latest_config
        latest_config.cluster = "invalid"
        latest_config.save()
        wl_app.refresh_from_db()
        with pytest.raises(Cluster.DoesNotExist):
            EnvClusterService(bk_stag_env).get_cluster()
