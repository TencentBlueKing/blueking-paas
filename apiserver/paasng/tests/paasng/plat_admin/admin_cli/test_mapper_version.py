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

from paas_wl.bk_app.applications.models.config import Config
from paasng.plat_admin.admin_cli.mapper_version import get_mapper_v1_envs

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.usefixtures("_with_wl_apps"),
]


class Test__get_mapper_v1_envs:
    def test_normal(self, bk_stag_env):
        assert len(list(get_mapper_v1_envs())) == 0

        # Update existent config object
        c = bk_stag_env.wl_app.latest_config
        c.metadata = {"mapper_version": "v1"}
        c.save()
        assert len(list(get_mapper_v1_envs())) == 1

    def test_multiple_configs(self, bk_stag_env):
        Config.objects.create(app_id=bk_stag_env.wl_app.uuid, metadata={"mapper_version": "v1"})
        assert len(list(get_mapper_v1_envs())) == 1

        # Newer config should override the mapper version value
        Config.objects.create(app_id=bk_stag_env.wl_app.uuid, metadata={"mapper_version": "v2"})
        assert len(list(get_mapper_v1_envs())) == 0
