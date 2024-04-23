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

from paasng.platform.mgrlegacy.cnative_migrations.wl_app import WlAppBackupManager
from paasng.platform.mgrlegacy.models import WlAppBackupRel

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_backup_manager(bk_stag_env):
    wl_app = bk_stag_env.wl_app
    manager = WlAppBackupManager(bk_stag_env)
    wl_app_backup = manager.create()

    assert manager.get().name == wl_app_backup.name
    assert manager.get().region == wl_app_backup.region
    assert wl_app_backup.latest_config.cluster == wl_app.latest_config.cluster
    assert wl_app_backup.namespace == wl_app.namespace
    assert wl_app_backup.module_name == wl_app.module_name
    assert WlAppBackupRel.objects.get(original_id=wl_app.uuid).backup_id == wl_app_backup.uuid
