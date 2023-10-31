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

from paas_wl.bk_app.cnative.specs.constants import DEFAULT_PROC_CPU, DEFAULT_PROC_MEM
from paas_wl.bk_app.cnative.specs.models import create_app_resource
from paas_wl.bk_app.cnative.specs.procs import CNativeProcSpec, parse_proc_specs
from paasng.platform.engine.constants import AppEnvName

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestParseProcSpecs:
    def test_default(self, bk_stag_wl_app):
        res = create_app_resource(bk_stag_wl_app.name, 'busybox')
        assert parse_proc_specs(res, AppEnvName.STAG) == [
            CNativeProcSpec('web', 1, 'start', DEFAULT_PROC_CPU, DEFAULT_PROC_MEM)
        ]

    def test_stopped(self, bk_stag_wl_app):
        res = create_app_resource(bk_stag_wl_app.name, 'busybox')
        res.spec.processes[0].replicas = 0
        assert parse_proc_specs(res, AppEnvName.STAG) == [
            CNativeProcSpec('web', 0, 'stop', DEFAULT_PROC_CPU, DEFAULT_PROC_MEM)
        ]
