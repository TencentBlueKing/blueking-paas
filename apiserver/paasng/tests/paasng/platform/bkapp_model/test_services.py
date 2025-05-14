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
from django.conf import settings
from django_dynamic_fixture import G

from paasng.platform.bkapp_model.entities.proc_service import ExposedType, ProcService
from paasng.platform.bkapp_model.fieldmgr import FieldManager, FieldMgrName, f_overlay_replicas
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.bkapp_model.services import check_replicas_manually_scaled, upsert_proc_svc_by_spec_version
from paasng.platform.declarative.constants import AppSpecVersion

pytestmark = pytest.mark.django_db(databases=["default"])


class Test__check_replicas_manually_scaled:
    @pytest.fixture()
    def module_process_spec(self, bk_module):
        return G(ModuleProcessSpec, module=bk_module, name="web")

    def test_scaled(self, bk_module, module_process_spec):
        FieldManager(bk_module, f_overlay_replicas(module_process_spec.name, "stag")).set(FieldMgrName.WEB_FORM)
        assert check_replicas_manually_scaled(bk_module) is True

    @pytest.mark.usefixtures("module_process_spec")
    def test_not_scaled(self, bk_module):
        assert check_replicas_manually_scaled(bk_module) is False

    def test_not_scaled_when_no_process(self, bk_module):
        """测试场景: 首次部署应用时, 还没有生成 ModuleProcessSpec 数据"""
        assert check_replicas_manually_scaled(bk_module) is False


class Test__upsert_proc_svc_by_spec_version:
    @pytest.fixture(autouse=True)
    def _create_module_specs(self, bk_module):
        G(ModuleProcessSpec, module=bk_module, name="web")
        G(ModuleProcessSpec, module=bk_module, name="backend")

    @pytest.mark.parametrize("spec_version", [None, AppSpecVersion.VER_1, AppSpecVersion.VER_2])
    def test_by_spec_version_lower_than_3(self, bk_module, spec_version):
        assert ModuleProcessSpec.objects.get(name="web", module=bk_module).services is None
        assert ModuleProcessSpec.objects.get(name="backend", module=bk_module).services is None

        upsert_proc_svc_by_spec_version(bk_module, spec_version)

        assert ModuleProcessSpec.objects.get(name="web", module=bk_module).services == [
            ProcService(
                name="web",
                target_port=settings.CONTAINER_PORT,
                protocol="TCP",
                exposed_type=ExposedType(),
                port=80,
            )
        ]
        assert ModuleProcessSpec.objects.get(name="backend", module=bk_module).services == [
            ProcService(name="backend", target_port=settings.CONTAINER_PORT, protocol="TCP", port=80)
        ]

    def test_by_spec_version_3(self, bk_module):
        assert ModuleProcessSpec.objects.get(name="web", module=bk_module).services is None
        assert ModuleProcessSpec.objects.get(name="backend", module=bk_module).services is None

        upsert_proc_svc_by_spec_version(bk_module, AppSpecVersion.VER_3)

        assert ModuleProcessSpec.objects.get(name="web", module=bk_module).services is None
        assert ModuleProcessSpec.objects.get(name="backend", module=bk_module).services is None
