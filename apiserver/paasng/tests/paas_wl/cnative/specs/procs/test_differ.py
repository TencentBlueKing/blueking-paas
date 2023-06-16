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
import copy

import pytest

from paas_wl.cnative.specs.models import create_app_resource
from paas_wl.cnative.specs.procs.differ import ProcReplicasChange, diff_replicas
from paasng.engine.constants import AppEnvName

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestDiffReplicas:
    def test_same(self, bk_stag_wl_app):
        res = create_app_resource(bk_stag_wl_app.name, 'busybox')
        assert diff_replicas(res, res, AppEnvName.STAG) == []

    def test_changed(self, bk_stag_wl_app):
        res = create_app_resource(bk_stag_wl_app.name, 'busybox')
        res_new = copy.deepcopy(res)
        res_new.spec.processes[0].replicas = 3
        assert diff_replicas(res, res_new, AppEnvName.STAG) == [ProcReplicasChange('web', 1, 3)]
