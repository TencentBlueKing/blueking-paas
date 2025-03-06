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

from paasng.platform.bkapp_model.fieldmgr import FieldManager, FieldMgrName, f_overlay_replicas
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.bkapp_model.services import check_replicas_manually_scaled

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
